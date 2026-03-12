"""
学术研究站 API Views
"""
import json
import threading
from pathlib import Path
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from core.context import get_user
from core import llm as _llm_module
from .models import (
    ResearchProject, Literature, LiteratureChunk,
    ResearchNote, ResearchConversation, ResearchMessage,
    ResearchIdea, WritingDraft,
)
from .indexer import chunk_literature, search_chunks


# ──────────────────────────────────────────────
# 研究项目 CRUD
# ──────────────────────────────────────────────

class ProjectListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = ResearchProject.objects.filter(user=request.user)
        data = []
        for p in projects:
            lit_count = p.literatures.count()
            note_count = p.notes.count()
            data.append({
                'id': p.id,
                'title': p.title,
                'description': p.description,
                'domain': p.domain,
                'research_questions': p.research_questions,
                'lit_count': lit_count,
                'note_count': note_count,
                'created_at': p.created_at.isoformat(),
                'updated_at': p.updated_at.isoformat(),
            })
        return Response(data)

    def post(self, request):
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'error': '项目标题不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        p = ResearchProject.objects.create(
            user=request.user,
            title=title,
            description=request.data.get('description', ''),
            domain=request.data.get('domain', ''),
            research_questions=request.data.get('research_questions', ''),
        )
        return Response({'id': p.id, 'title': p.title}, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_project(self, request, pk):
        return ResearchProject.objects.filter(id=pk, user=request.user).first()

    def get(self, request, pk):
        p = self._get_project(request, pk)
        if not p:
            return Response({'error': '项目不存在'}, status=404)
        return Response({
            'id': p.id, 'title': p.title, 'description': p.description,
            'domain': p.domain, 'research_questions': p.research_questions,
            'metadata': p.metadata,
            'created_at': p.created_at.isoformat(),
        })

    def put(self, request, pk):
        p = self._get_project(request, pk)
        if not p:
            return Response({'error': '项目不存在'}, status=404)
        for field in ['title', 'description', 'domain', 'research_questions']:
            if field in request.data:
                setattr(p, field, request.data[field])
        p.save()
        return Response({'ok': True})

    def delete(self, request, pk):
        p = self._get_project(request, pk)
        if not p:
            return Response({'error': '项目不存在'}, status=404)
        p.delete()
        return Response({'ok': True})


# ──────────────────────────────────────────────
# 文献管理
# ──────────────────────────────────────────────

class LiteratureListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        lits = Literature.objects.filter(
            project_id=project_id,
            user=request.user
        )
        data = []
        for lit in lits:
            data.append({
                'id': lit.id,
                'title': lit.title,
                'authors': lit.authors,
                'year': lit.year,
                'journal': lit.journal,
                'abstract': lit.abstract[:300] if lit.abstract else '',
                'language': lit.language,
                'source_type': lit.source_type,
                'is_indexed': lit.is_indexed,
                'is_shared': lit.is_shared,
                'total_lines': lit.total_lines,
                'file_ref': lit.get_file_ref(),
                'chunk_count': lit.chunks.count(),
                'created_at': lit.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request, project_id):
        """创建文献（手动录入MD内容）"""
        title = request.data.get('title', '').strip()
        if not title:
            return Response({'error': '文献标题不能为空'}, status=400)

        # 检查项目归属
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)

        content = request.data.get('content', '')
        lit = Literature.objects.create(
            user=request.user,
            project=project,
            title=title,
            authors=request.data.get('authors', ''),
            year=request.data.get('year', ''),
            journal=request.data.get('journal', ''),
            abstract=request.data.get('abstract', ''),
            content=content,
            language=request.data.get('language', 'zh'),
            source_type='manual',
            file_path=f"papers/{title[:30].replace(' ', '_')}.md",
        )

        if content:
            threading.Thread(target=chunk_literature, args=(lit,)).start()

        return Response({'id': lit.id, 'title': lit.title}, status=201)


class LiteratureImportOCRView(APIView):
    """从OCR工作室导入文献"""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        from ocr_studio.models import OCRProject, OCRPage

        ocr_project_id = request.data.get('ocr_project_id', '')
        title = request.data.get('title', '').strip()

        if not ocr_project_id:
            return Response({'error': '请提供OCR项目ID'}, status=400)

        try:
            ocr_proj = OCRProject.objects.get(id=ocr_project_id, user=request.user)
        except OCRProject.DoesNotExist:
            return Response({'error': 'OCR项目不存在或无权访问'}, status=404)

        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '研究项目不存在'}, status=404)

        # 拼接OCR结果
        pages = OCRPage.objects.filter(project=ocr_proj, ocr_status='done').order_by('page_num')
        parts = []
        for p in pages:
            if p.ocr_result:
                parts.append(f"<!-- Page {p.page_num} -->\n\n{p.ocr_result}")
        content = "\n\n---\n\n".join(parts)

        if not content:
            return Response({'error': 'OCR项目没有已完成的页面结果'}, status=400)

        if not title:
            title = ocr_proj.name.rsplit('.', 1)[0] if '.' in ocr_proj.name else ocr_proj.name

        lit = Literature.objects.create(
            user=request.user,
            project=project,
            title=title,
            content=content,
            source_type='ocr',
            source_ocr_id=ocr_project_id,
            language=request.data.get('language', 'en'),
            authors=request.data.get('authors', ''),
            year=request.data.get('year', ''),
            journal=request.data.get('journal', ''),
            abstract=request.data.get('abstract', ''),
            file_path=f"papers/{ocr_proj.name.rsplit('.', 1)[0]}.md",
        )

        # 后台建立索引
        threading.Thread(target=chunk_literature, args=(lit,)).start()

        return Response({
            'id': lit.id,
            'title': lit.title,
            'total_pages': ocr_proj.total_pages,
        }, status=201)


class LiteratureDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_lit(self, request, lit_id):
        return Literature.objects.filter(
            id=lit_id
        ).filter(
            user=request.user
        ).first() or Literature.objects.filter(
            id=lit_id, is_shared=True
        ).first()

    def get(self, request, lit_id):
        lit = self._get_lit(request, lit_id)
        if not lit:
            return Response({'error': '文献不存在'}, status=404)
        return Response({
            'id': lit.id,
            'title': lit.title,
            'authors': lit.authors,
            'year': lit.year,
            'journal': lit.journal,
            'abstract': lit.abstract,
            'content': lit.content,
            'language': lit.language,
            'source_type': lit.source_type,
            'is_indexed': lit.is_indexed,
            'is_shared': lit.is_shared,
            'total_lines': lit.total_lines,
            'file_ref': lit.get_file_ref(),
            'keywords_meta': lit.keywords_meta,
            'created_at': lit.created_at.isoformat(),
        })

    def put(self, request, lit_id):
        lit = Literature.objects.filter(id=lit_id, user=request.user).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)
        for field in ['title', 'authors', 'year', 'journal', 'abstract',
                      'language', 'is_shared', 'keywords_meta']:
            if field in request.data:
                setattr(lit, field, request.data[field])
        if 'content' in request.data:
            lit.content = request.data['content']
            threading.Thread(target=chunk_literature, args=(lit,)).start()
        else:
            lit.save()
        return Response({'ok': True})

    def delete(self, request, lit_id):
        lit = Literature.objects.filter(id=lit_id, user=request.user).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)
        lit.delete()
        return Response({'ok': True})


class LiteratureReindexView(APIView):
    """重新建立文献索引"""
    permission_classes = [IsAuthenticated]

    def post(self, request, lit_id):
        lit = Literature.objects.filter(id=lit_id, user=request.user).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)
        threading.Thread(target=chunk_literature, args=(lit,)).start()
        return Response({'ok': True, 'message': '正在重新建立索引...'})


class LiteratureContentView(APIView):
    """获取文献内容（支持行范围）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, lit_id):
        lit = Literature.objects.filter(id=lit_id).filter(
            user=request.user
        ).first() or Literature.objects.filter(id=lit_id, is_shared=True).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)

        line_start = request.query_params.get('line_start')
        line_end = request.query_params.get('line_end')

        lines = lit.content.splitlines()
        if line_start and line_end:
            try:
                ls = max(1, int(line_start)) - 1
                le = min(len(lines), int(line_end))
                content = '\n'.join(lines[ls:le])
            except (ValueError, TypeError):
                content = lit.content
        else:
            content = lit.content

        return Response({
            'content': content,
            'total_lines': len(lines),
            'file_ref': lit.get_file_ref(),
        })


class LiteratureChunksView(APIView):
    """获取文献的所有块（用于结构导航）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, lit_id):
        lit = Literature.objects.filter(id=lit_id).filter(
            user=request.user
        ).first() or Literature.objects.filter(id=lit_id, is_shared=True).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)

        chunks = LiteratureChunk.objects.filter(literature=lit).values(
            'id', 'chunk_index', 'line_start', 'line_end',
            'heading', 'chunk_type', 'importance'
        )
        return Response(list(chunks))


class LiteratureAnalysisView(APIView):
    """分析文献结构"""
    permission_classes = [IsAuthenticated]

    def get(self, request, lit_id):
        from .agent import analyze_literature_structure
        lit = Literature.objects.filter(id=lit_id).filter(
            user=request.user
        ).first() or Literature.objects.filter(id=lit_id, is_shared=True).first()
        if not lit:
            return Response({'error': '文献不存在'}, status=404)
        if not lit.is_indexed:
            return Response({'error': '文献尚未建立索引，请先索引'}, status=400)

        project_id = lit.project_id
        analysis = analyze_literature_structure(lit.id, project_id)
        return Response(analysis)


# ──────────────────────────────────────────────
# 知识检索
# ──────────────────────────────────────────────

class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        query = request.data.get('query', '').strip()
        if not query:
            return Response({'error': '查询不能为空'}, status=400)

        top_k = min(int(request.data.get('top_k', 10)), 30)
        lit_ids = request.data.get('lit_ids', None)

        scored = search_chunks(project_id, query, request.user.id, top_k=top_k, lit_ids=lit_ids)

        results = []
        for chunk, score in scored:
            results.append({
                'chunk_id': chunk.id,
                'lit_id': chunk.literature_id,
                'lit_title': chunk.literature.title,
                'lit_authors': chunk.literature.authors,
                'lit_year': chunk.literature.year,
                'file_ref': chunk.literature.get_file_ref(),
                'line_start': chunk.line_start,
                'line_end': chunk.line_end,
                'heading': chunk.heading,
                'chunk_type': chunk.chunk_type,
                'cite_key': chunk.get_citation(),
                'cite_display': chunk.get_citation_display(),
                'preview': chunk.content[:400],
                'score': round(score, 3),
            })

        return Response({'results': results, 'total': len(results), 'query': query})


class ExploreView(APIView):
    """深度文献探索"""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        from .agent import explore_literature
        query = request.data.get('query', '').strip()
        depth = min(int(request.data.get('depth', 2)), 3)
        if not query:
            return Response({'error': '查询不能为空'}, status=400)

        result = explore_literature(project_id, request.user.id, query, depth)
        return Response(result)


# ──────────────────────────────────────────────
# 研究对话
# ──────────────────────────────────────────────

class ConversationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        convs = ResearchConversation.objects.filter(
            user=request.user, project_id=project_id
        )
        data = [{
            'id': c.id,
            'title': c.title,
            'msg_count': c.messages.count(),
            'updated_at': c.updated_at.isoformat(),
        } for c in convs]
        return Response(data)

    def post(self, request, project_id):
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)
        conv = ResearchConversation.objects.create(
            user=request.user, project=project,
            title=request.data.get('title', '新对话')
        )
        return Response({'id': conv.id, 'title': conv.title}, status=201)


class ConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conv_id):
        conv = ResearchConversation.objects.filter(id=conv_id, user=request.user).first()
        if not conv:
            return Response({'error': '对话不存在'}, status=404)
        msgs = conv.messages.all()
        return Response({
            'id': conv.id,
            'title': conv.title,
            'messages': [{
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'citations': m.citations,
                'created_at': m.created_at.isoformat(),
            } for m in msgs]
        })

    def delete(self, request, conv_id):
        conv = ResearchConversation.objects.filter(id=conv_id, user=request.user).first()
        if not conv:
            return Response({'error': '对话不存在'}, status=404)
        conv.delete()
        return Response({'ok': True})


class ConversationChatStreamView(APIView):
    """流式研究对话"""
    permission_classes = [IsAuthenticated]

    def post(self, request, conv_id):
        conv = ResearchConversation.objects.filter(id=conv_id, user=request.user).first()
        if not conv:
            return Response({'error': '对话不存在'}, status=404)

        message = request.data.get('message', '').strip()
        if not message:
            return Response({'error': '消息不能为空'}, status=400)

        project_id = conv.project_id
        user_id = request.user.id

        try:
            config = _llm_module._get_config()
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        from .agent import research_chat_stream

        def generate():
            yield from research_chat_stream(
                project_id, conv_id, message, user_id,
                user_id_ctx=user_id, config=config
            )

        response = StreamingHttpResponse(generate(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


# ──────────────────────────────────────────────
# 研究笔记
# ──────────────────────────────────────────────

class NoteListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        notes = ResearchNote.objects.filter(
            user=request.user, project_id=project_id
        ).select_related('literature')
        data = [{
            'id': n.id,
            'note_type': n.note_type,
            'title': n.title,
            'content': n.content,
            'lit_id': n.literature_id,
            'lit_title': n.literature.title if n.literature else '',
            'cited_line_start': n.cited_line_start,
            'cited_line_end': n.cited_line_end,
            'cited_text': n.cited_text,
            'citation': n.get_citation(),
            'tags': n.tags,
            'created_at': n.created_at.isoformat(),
        } for n in notes]
        return Response(data)

    def post(self, request, project_id):
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)

        note = ResearchNote.objects.create(
            user=request.user,
            project=project,
            literature_id=request.data.get('lit_id'),
            note_type=request.data.get('note_type', 'annotation'),
            title=request.data.get('title', ''),
            content=request.data.get('content', ''),
            cited_line_start=request.data.get('cited_line_start'),
            cited_line_end=request.data.get('cited_line_end'),
            cited_text=request.data.get('cited_text', ''),
            tags=request.data.get('tags', []),
        )
        return Response({
            'id': note.id,
            'citation': note.get_citation(),
        }, status=201)


class NoteDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, note_id):
        note = ResearchNote.objects.filter(id=note_id, user=request.user).first()
        if not note:
            return Response({'error': '笔记不存在'}, status=404)
        for field in ['title', 'content', 'note_type', 'tags']:
            if field in request.data:
                setattr(note, field, request.data[field])
        note.save()
        return Response({'ok': True})

    def delete(self, request, note_id):
        note = ResearchNote.objects.filter(id=note_id, user=request.user).first()
        if not note:
            return Response({'error': '笔记不存在'}, status=404)
        note.delete()
        return Response({'ok': True})


# ──────────────────────────────────────────────
# 研究灵感
# ──────────────────────────────────────────────

class IdeaListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        ideas = ResearchIdea.objects.filter(
            user=request.user, project_id=project_id
        )
        data = []
        for idea in ideas:
            chunks = idea.evidence_chunks.all()[:3]
            data.append({
                'id': idea.id,
                'idea_type': idea.idea_type,
                'title': idea.title,
                'description': idea.description,
                'evidence_summary': idea.evidence_summary,
                'confidence': idea.confidence,
                'is_starred': idea.is_starred,
                'evidence_chunks': [{
                    'cite': c.get_citation(),
                    'preview': c.content[:150],
                } for c in chunks],
                'created_at': idea.created_at.isoformat(),
            })
        return Response(data)

    def post(self, request, project_id):
        """手动创建灵感"""
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)
        idea = ResearchIdea.objects.create(
            user=request.user, project=project,
            idea_type=request.data.get('idea_type', 'gap'),
            title=request.data.get('title', ''),
            description=request.data.get('description', ''),
            evidence_summary=request.data.get('evidence_summary', ''),
        )
        return Response({'id': idea.id}, status=201)


class IdeaGenerateView(APIView):
    """AI生成研究灵感"""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        from .agent import generate_ideas
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)

        focus_query = request.data.get('focus_query', '')
        lit_ids = request.data.get('lit_ids', None)

        ideas = generate_ideas(project_id, request.user.id, focus_query, lit_ids)
        data = [{
            'id': idea.id,
            'idea_type': idea.idea_type,
            'title': idea.title,
            'description': idea.description,
            'evidence_summary': idea.evidence_summary,
        } for idea in ideas]
        return Response({'ideas': data})


class IdeaDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, idea_id):
        idea = ResearchIdea.objects.filter(id=idea_id, user=request.user).first()
        if not idea:
            return Response({'error': '灵感不存在'}, status=404)
        if 'is_starred' in request.data:
            idea.is_starred = request.data['is_starred']
        if 'description' in request.data:
            idea.description = request.data['description']
        idea.save()
        return Response({'ok': True})

    def delete(self, request, idea_id):
        idea = ResearchIdea.objects.filter(id=idea_id, user=request.user).first()
        if not idea:
            return Response({'error': '灵感不存在'}, status=404)
        idea.delete()
        return Response({'ok': True})


# ──────────────────────────────────────────────
# 写作草稿
# ──────────────────────────────────────────────

class DraftListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        drafts = WritingDraft.objects.filter(user=request.user, project_id=project_id)
        data = [{
            'id': d.id,
            'title': d.title,
            'word_count': d.word_count,
            'updated_at': d.updated_at.isoformat(),
        } for d in drafts]
        return Response(data)

    def post(self, request, project_id):
        project = ResearchProject.objects.filter(id=project_id, user=request.user).first()
        if not project:
            return Response({'error': '项目不存在'}, status=404)
        draft = WritingDraft.objects.create(
            user=request.user, project=project,
            title=request.data.get('title', '新草稿'),
            content=request.data.get('content', ''),
            outline=request.data.get('outline', ''),
        )
        return Response({'id': draft.id, 'title': draft.title}, status=201)


class DraftDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, draft_id):
        draft = WritingDraft.objects.filter(id=draft_id, user=request.user).first()
        if not draft:
            return Response({'error': '草稿不存在'}, status=404)
        return Response({
            'id': draft.id,
            'title': draft.title,
            'content': draft.content,
            'outline': draft.outline,
            'word_count': draft.word_count,
            'updated_at': draft.updated_at.isoformat(),
        })

    def put(self, request, draft_id):
        draft = WritingDraft.objects.filter(id=draft_id, user=request.user).first()
        if not draft:
            return Response({'error': '草稿不存在'}, status=404)
        for field in ['title', 'content', 'outline']:
            if field in request.data:
                setattr(draft, field, request.data[field])
        draft.save()
        return Response({'ok': True, 'word_count': draft.word_count})

    def delete(self, request, draft_id):
        draft = WritingDraft.objects.filter(id=draft_id, user=request.user).first()
        if not draft:
            return Response({'error': '草稿不存在'}, status=404)
        draft.delete()
        return Response({'ok': True})


class DraftWritingAssistView(APIView):
    """流式写作辅助"""
    permission_classes = [IsAuthenticated]

    def post(self, request, draft_id):
        draft = WritingDraft.objects.filter(id=draft_id, user=request.user).first()
        if not draft:
            return Response({'error': '草稿不存在'}, status=404)

        instruction = request.data.get('instruction', '').strip()
        if not instruction:
            return Response({'error': '请提供写作指令'}, status=400)

        section_context = request.data.get('section_context', '')
        project_id = draft.project_id
        user_id = request.user.id

        try:
            config = _llm_module._get_config()
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        from .agent import assist_writing_stream

        def generate():
            yield from assist_writing_stream(
                project_id, draft_id, instruction, user_id,
                section_context=section_context,
                user_id_ctx=user_id, config=config
            )

        response = StreamingHttpResponse(generate(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


# ──────────────────────────────────────────────
# OCR 项目列表（供导入使用）
# ──────────────────────────────────────────────

class OCRProjectsForImportView(APIView):
    """获取当前用户可导入的OCR项目"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from ocr_studio.models import OCRProject, OCRPage
        projects = OCRProject.objects.filter(user=request.user).order_by('-created_at')
        data = []
        for p in projects:
            done = p.pages.filter(ocr_status='done').count()
            total = p.total_pages
            data.append({
                'id': p.id,
                'name': p.name,
                'total_pages': total,
                'done_pages': done,
                'created_at': p.created_at.isoformat(),
                'can_import': done > 0,
            })
        return Response(data)


# ──────────────────────────────────────────────
# Token 统计（复用现有系统）
# ──────────────────────────────────────────────

class TokenStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from accounts.models import TokenUsage
        usage, _ = TokenUsage.objects.get_or_create(user=request.user)
        return Response({
            'total_tokens': usage.total_tokens,
            'input_tokens': usage.input_tokens,
            'output_tokens': usage.output_tokens,
            'prompt_count': usage.prompt_count,
            'daily_total': usage.daily_input_tokens + usage.daily_output_tokens,
            'daily_input': usage.daily_input_tokens,
            'daily_output': usage.daily_output_tokens,
            'daily_count': usage.daily_prompt_count,
        })
