import json
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly

from .models import CodeProject, CodeFile, FileVersion, CodeSession, CodeMessage
from . import agent as _agent
from .security import validate_upload_file, validate_batch_upload, get_upload_limits
from memory.pyramid import get_pyramid_stats


def _token_auth(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=auth[6:].strip()).user
    except Exception:
        return None


# ─────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────

class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = CodeProject.objects.filter(user=request.user) if request.user.is_authenticated else CodeProject.objects.none()
        return Response([{
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'language': p.language,
            'file_count': p.files.count(),
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
        } for p in qs])

    def post(self, request):
        data = request.data
        project = CodeProject.objects.create(
            user=request.user,
            name=data.get('name', '新项目'),
            description=data.get('description', ''),
            language=data.get('language', ''),
        )
        return Response({'id': project.id, 'name': project.name}, status=201)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get(self, project_id, user):
        try:
            p = CodeProject.objects.get(id=project_id)
        except CodeProject.DoesNotExist:
            return None
        if p.user and p.user != user:
            return None
        return p

    def get(self, request, project_id):
        p = self._get(project_id, request.user)
        if not p:
            return Response({'error': '未找到'}, status=404)
        files = CodeFile.objects.filter(project=p)
        return Response({
            'id': p.id,
            'name': p.name,
            'description': p.description,
            'language': p.language,
            'metadata': p.metadata,
            'files': [{'id': f.id, 'path': f.path, 'language': f.language,
                       'size': f.size, 'current_version': f.current_version,
                       'updated_at': f.updated_at.isoformat()} for f in files],
            'created_at': p.created_at.isoformat(),
        })

    def put(self, request, project_id):
        p = self._get(project_id, request.user)
        if not p:
            return Response({'error': '未找到'}, status=404)
        for field in ['name', 'description', 'language']:
            if field in request.data:
                setattr(p, field, request.data[field])
        p.save()
        return Response({'id': p.id, 'updated': True})

    def delete(self, request, project_id):
        p = self._get(project_id, request.user)
        if not p:
            return Response({'error': '未找到'}, status=404)
        # Clean up memory nodes
        try:
            from memory.models import MemoryNode
            MemoryNode.objects.filter(project_id=p.memory_project_id).delete()
        except Exception:
            pass
        p.delete()
        return Response({'deleted': True})


# ─────────────────────────────────────────────
# Files
# ─────────────────────────────────────────────

class FileListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        """Create or overwrite a single file."""
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '项目未找到'}, status=404)

        data = request.data
        path = data.get('path', '').strip().lstrip('/')
        content = data.get('content', '')
        language = data.get('language', '') or _agent._detect_language(path)

        if not path:
            return Response({'error': '需要提供文件路径'}, status=400)

        sec = validate_upload_file(path, content)
        if not sec['valid']:
            return Response({'error': sec['reason']}, status=400)

        file_obj, created = CodeFile.objects.get_or_create(
            project=project, path=path,
            defaults={'content': content, 'language': language}
        )
        if not created:
            # Save snapshot before overwrite
            FileVersion.objects.get_or_create(
                file=file_obj, version=file_obj.current_version,
                defaults={'content': file_obj.content, 'change_summary': '上传覆盖前快照'}
            )
            file_obj.content = content
            file_obj.language = language or file_obj.language
            file_obj.save()

        # Index into memory pyramid
        try:
            _agent.index_file(project.memory_project_id, path, content, language)
        except Exception:
            pass

        return Response({'id': file_obj.id, 'path': file_obj.path,
                         'created': created, 'size': file_obj.size}, status=201 if created else 200)


class FileBatchUploadView(APIView):
    """Upload multiple files at once (e.g., after directory selection in browser)."""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '项目未找到'}, status=404)

        files_data = request.data.get('files', [])
        if not files_data:
            return Response({'error': '没有文件数据'}, status=400)

        existing_count = CodeFile.objects.filter(project=project).count()
        sec_result = validate_batch_upload(files_data, existing_count)

        if sec_result['error']:
            return Response({'error': sec_result['error']}, status=400)

        saved = []
        for item in sec_result['allowed']:
            path = item['path']
            content = item['content']
            language = _agent._detect_language(path)
            file_obj, created = CodeFile.objects.get_or_create(
                project=project, path=path,
                defaults={'content': content, 'language': language}
            )
            if not created:
                file_obj.content = content
                file_obj.language = language
                file_obj.save()
            entry = {'path': path, 'created': created}
            if item.get('warning'):
                entry['warning'] = item['warning']
            saved.append(entry)

        # Bulk index into memory
        try:
            all_files = CodeFile.objects.filter(project=project)
            _agent.index_project_files(project.memory_project_id, all_files)
        except Exception:
            pass

        response_data = {'saved': len(saved), 'files': saved}
        if sec_result['rejected']:
            response_data['rejected'] = sec_result['rejected']
        status_code = 207 if sec_result['rejected'] else 200
        return Response(response_data, status=status_code)


class FileDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        return Response({
            'id': f.id, 'project_id': f.project_id,
            'path': f.path, 'content': f.content,
            'language': f.language, 'size': f.size,
            'current_version': f.current_version,
            'updated_at': f.updated_at.isoformat(),
        })

    def put(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        if f.project.user and f.project.user != request.user:
            return Response({'error': '无权操作'}, status=403)

        new_content = request.data.get('content', f.content)
        change_summary = request.data.get('change_summary', '手动编辑')

        # Save snapshot before update
        FileVersion.objects.get_or_create(
            file=f, version=f.current_version,
            defaults={'content': f.content, 'change_summary': change_summary}
        )
        f.current_version += 1
        f.content = new_content
        f.save()

        # Re-index into memory
        try:
            _agent.index_file(f.project.memory_project_id, f.path, new_content, f.language)
        except Exception:
            pass

        return Response({'id': f.id, 'updated': True,
                         'current_version': f.current_version, 'size': f.size})

    def delete(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        if f.project.user and f.project.user != request.user:
            return Response({'error': '无权操作'}, status=403)
        f.delete()
        return Response({'deleted': True})


class FileVersionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, file_id):
        try:
            f = CodeFile.objects.get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        versions = FileVersion.objects.filter(file=f)
        return Response([{
            'version': v.version, 'change_summary': v.change_summary,
            'size': len(v.content), 'created_at': v.created_at.isoformat(),
        } for v in versions])


class FileRollbackView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        if f.project.user and f.project.user != request.user:
            return Response({'error': '无权操作'}, status=403)

        target_version = request.data.get('version')
        if target_version is None:
            return Response({'error': '需要指定目标版本号'}, status=400)

        try:
            snap = FileVersion.objects.get(file=f, version=int(target_version))
        except FileVersion.DoesNotExist:
            return Response({'error': f'版本 {target_version} 不存在'}, status=404)

        # Save current state as a new snapshot before rollback
        FileVersion.objects.get_or_create(
            file=f, version=f.current_version,
            defaults={'content': f.content, 'change_summary': f'回滚前快照（回滚到v{target_version}）'}
        )
        f.current_version += 1
        f.content = snap.content
        f.save()

        return Response({'rolled_back_to': target_version,
                         'current_version': f.current_version})


# ─────────────────────────────────────────────
# Apply Confirmed Diffs
# ─────────────────────────────────────────────

class ApplyDiffsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        if f.project.user and f.project.user != request.user:
            return Response({'error': '无权操作'}, status=403)

        accepted_diffs = request.data.get('diffs', [])
        change_summary = request.data.get('change_summary', 'AI编辑建议')
        message_id = request.data.get('message_id')

        if not accepted_diffs:
            return Response({'error': '没有要应用的修改'}, status=400)

        # Save snapshot
        FileVersion.objects.get_or_create(
            file=f, version=f.current_version,
            defaults={'content': f.content,
                      'change_summary': f'应用AI建议前快照 — {change_summary}'}
        )

        # Apply diffs via shared core/diff_agent
        new_content, applied = _agent.apply_confirmed_diffs(
            f.project.memory_project_id, f.path, f.content, accepted_diffs
        )
        f.current_version += 1
        f.content = new_content
        f.save()

        # Mark message as applied
        if message_id:
            try:
                msg = CodeMessage.objects.get(id=message_id)
                msg.diffs_applied = True
                msg.save(update_fields=['diffs_applied'])
            except CodeMessage.DoesNotExist:
                pass

        # Save version record
        FileVersion.objects.create(
            file=f, version=f.current_version,
            content=new_content, change_summary=change_summary,
            diffs_applied=applied
        )

        # Re-index file into memory after edit
        try:
            _agent.index_file(f.project.memory_project_id, f.path, new_content, f.language)
        except Exception:
            pass

        return Response({
            'applied_count': len(applied),
            'current_version': f.current_version,
            'new_content': new_content,
        })


# ─────────────────────────────────────────────
# Sessions & Chat
# ─────────────────────────────────────────────

class SessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        sessions = CodeSession.objects.filter(project=project)
        return Response([{
            'id': s.id, 'title': s.title,
            'focused_file_id': s.focused_file_id,
            'created_at': s.created_at.isoformat(),
        } for s in sessions])

    def post(self, request, project_id):
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        focused_file_id = request.data.get('focused_file_id')
        focused_file = None
        if focused_file_id:
            try:
                focused_file = CodeFile.objects.get(id=focused_file_id, project=project)
            except CodeFile.DoesNotExist:
                pass
        session = CodeSession.objects.create(
            project=project,
            focused_file=focused_file,
            title=request.data.get('title', '新对话'),
        )
        return Response({'id': session.id, 'title': session.title}, status=201)


class SessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            s = CodeSession.objects.select_related('project').get(id=session_id)
        except CodeSession.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        messages = CodeMessage.objects.filter(session=s)
        return Response({
            'id': s.id, 'title': s.title,
            'project_id': s.project_id,
            'focused_file_id': s.focused_file_id,
            'messages': [{
                'id': m.id, 'role': m.role, 'content': m.content,
                'pending_diffs': m.pending_diffs,
                'diffs_applied': m.diffs_applied,
                'created_at': m.created_at.isoformat(),
            } for m in messages],
        })

    def delete(self, request, session_id):
        try:
            s = CodeSession.objects.select_related('project').get(id=session_id)
        except CodeSession.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        if s.project.user and s.project.user != request.user:
            return Response({'error': '无权操作'}, status=403)
        s.delete()
        return Response({'deleted': True})


# ─────────────────────────────────────────────
# Streaming Views (SSE)
# ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class ChatStreamView(View):
    """流式代码对话 — 复用 memory/pyramid 上下文 + core/llm.chat_stream"""

    def post(self, request, session_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        user_message = data.get('message', '').strip()
        current_file_id = data.get('file_id')
        current_file_path = ''
        current_file_content = ''

        if not user_message:
            return JsonResponse({'error': '消息不能为空'}, status=400)

        try:
            session = CodeSession.objects.select_related('project').get(id=session_id)
        except CodeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)
        if session.project.user and session.project.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        # Load current file content if provided
        if current_file_id:
            try:
                cf = CodeFile.objects.get(id=current_file_id, project=session.project)
                current_file_path = cf.path
                current_file_content = cf.content
            except CodeFile.DoesNotExist:
                pass

        # Save user message
        CodeMessage.objects.create(session=session, role='user', content=user_message)

        # Build conversation history
        recent_msgs = list(CodeMessage.objects.filter(session=session).order_by('-created_at')[:20])
        recent_msgs.reverse()
        messages = [{'role': m.role, 'content': m.content} for m in recent_msgs]

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        project = session.project

        def generate():
            try:
                yield from _agent.code_chat_stream(
                    memory_project_id=project.memory_project_id,
                    project_name=project.name,
                    language=project.language,
                    session_id=session_id,
                    messages=messages,
                    current_file_path=current_file_path,
                    current_file_content=current_file_content,
                    user_id=user.id,
                    config=config,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


@method_decorator(csrf_exempt, name='dispatch')
class SuggestEditsStreamView(View):
    """流式代码编辑建议 — 使用与小说润色相同的 diff 格式"""

    def post(self, request, file_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        instruction = data.get('instruction', '').strip()
        if not instruction:
            return JsonResponse({'error': '需要提供修改指令'}, status=400)

        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return JsonResponse({'error': '文件未找到'}, status=404)
        if f.project.user and f.project.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        # Save pending AI message (diffs filled in after streaming)
        ai_msg = CodeMessage.objects.create(
            session_id=None,   # standalone suggest, no session required
            role='assistant',
            content=f'正在为 {f.path} 生成修改建议...',
        ) if False else None  # we create after streaming in apply flow

        project = f.project

        def generate():
            try:
                yield from _agent.suggest_edits_stream(
                    memory_project_id=project.memory_project_id,
                    project_name=project.name,
                    language=project.language,
                    file_path=f.path,
                    file_content=f.content,
                    instruction=instruction,
                    user_id=user.id,
                    config=config,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


@method_decorator(csrf_exempt, name='dispatch')
class GenerateCodeStreamView(View):
    """流式代码生成（新函数/新模块）"""

    def post(self, request, project_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        try:
            project = CodeProject.objects.get(id=project_id, user=user)
        except CodeProject.DoesNotExist:
            return JsonResponse({'error': '项目未找到'}, status=404)

        data = json.loads(request.body or b'{}')
        instruction = data.get('instruction', '').strip()
        context_hint = data.get('context_hint', '')
        if not instruction:
            return JsonResponse({'error': '需要描述要生成的代码'}, status=400)

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        def generate():
            try:
                yield from _agent.generate_code_stream(
                    memory_project_id=project.memory_project_id,
                    project_name=project.name,
                    language=project.language,
                    instruction=instruction,
                    context_hint=context_hint,
                    user_id=user.id,
                    config=config,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


# ─────────────────────────────────────────────
# Utility Views
# ─────────────────────────────────────────────

class ExplainCodeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, file_id):
        try:
            f = CodeFile.objects.select_related('project').get(id=file_id)
        except CodeFile.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        selected_code = request.data.get('selected_code', '')
        question = request.data.get('question', '')
        if not selected_code:
            return Response({'error': '需要提供选中代码'}, status=400)
        explanation = _agent.explain_code(
            f.project.memory_project_id, f.project.name,
            f.project.language, f.path, selected_code, question
        )
        return Response({'explanation': explanation})


class AnalyzeProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        summary = _agent.analyze_project(project.memory_project_id, project.name)
        return Response({'summary': summary})


class MemoryStatsView(APIView):
    """显示代码项目的记忆金字塔统计，与小说 memory stats 完全复用同一函数"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            project = CodeProject.objects.get(id=project_id, user=request.user)
        except CodeProject.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        stats = get_pyramid_stats(project.memory_project_id)
        return Response(stats)


class UploadLimitsView(APIView):
    """返回当前服务端上传限制配置，供前端展示。"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(get_upload_limits())


# ─────────────────────────────────────────────
# 本地模式：无状态 SSE 端点（文件内容不写入任何 DB）
# ─────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class LocalSuggestView(View):
    """
    本地模式 AI 编辑建议（SSE 流式）。
    接收文件内容，返回 diff 建议，不存储任何内容。
    """

    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        file_path = data.get('file_path', 'unknown').strip()
        content = data.get('content', '')
        instruction = data.get('instruction', '').strip()
        context_files = data.get('context_files', [])

        if not instruction:
            return JsonResponse({'error': '需要提供修改指令'}, status=400)
        if not content:
            return JsonResponse({'error': '需要提供文件内容'}, status=400)

        # 大小限制：当前文件 + 上下文文件总计不超过 1MB（防止滥用）
        total_size = len(content.encode('utf-8', errors='replace'))
        for cf in context_files[:5]:
            total_size += len(cf.get('content', '').encode('utf-8', errors='replace'))
        if total_size > 1024 * 1024:
            return JsonResponse({'error': '文件内容总大小超过 1MB 限制'}, status=400)

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        def generate():
            try:
                yield from _agent.suggest_edits_stream_local(
                    file_path=file_path,
                    content=content,
                    instruction=instruction,
                    context_files=context_files,
                    config=config,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


@method_decorator(csrf_exempt, name='dispatch')
class LocalChatView(View):
    """
    本地模式代码对话（SSE 流式）。
    接收文件内容和对话历史，返回 AI 回复，不存储任何内容。
    """

    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        message = data.get('message', '').strip()
        current_file = data.get('current_file')   # {'path': str, 'content': str}
        context_files = data.get('context_files', [])
        history = data.get('history', [])

        if not message:
            return JsonResponse({'error': '消息不能为空'}, status=400)

        # 大小限制
        total_size = len(message.encode('utf-8', errors='replace'))
        if current_file:
            total_size += len(current_file.get('content', '').encode('utf-8', errors='replace'))
        for cf in context_files[:5]:
            total_size += len(cf.get('content', '').encode('utf-8', errors='replace'))
        if total_size > 1024 * 1024:
            return JsonResponse({'error': '内容总大小超过 1MB 限制'}, status=400)

        from core.llm import _get_config
        try:
            config = _get_config()
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        def generate():
            try:
                yield from _agent.local_chat_stream(
                    message=message,
                    current_file=current_file,
                    context_files=context_files,
                    history=history,
                    config=config,
                )
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp
