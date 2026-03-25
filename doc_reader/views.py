"""
文档阅读器后端视图

功能：
1. 文档项目管理（创建、列表、删除）
2. 云盘文件集成
3. PDF页面缓存
4. GLM-OCR解析
5. LLM对话（带预设指令）
6. 缓存配额管理
"""
import base64
import json
import uuid
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView, RetrieveDestroyAPIView
from django.http import StreamingHttpResponse
from django.db.models import Sum, Q
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile
from io import BytesIO

from core.models import APIConfig
from core.auth import _token_auth
from core.llm import chat_stream, _get_config
from .models import (
    DocumentProject, DocumentPage, ParseSession,
    ChatSession, ChatMessage, USER_CACHE_QUOTA_BYTES
)


# ==================== 工具函数 ====================

def generate_project_id():
    """生成12位项目ID"""
    return uuid.uuid4().hex[:12].upper()


def get_user_cache_usage(user):
    """获取用户缓存使用情况"""
    used = DocumentPage.objects.filter(
        document__user=user
    ).aggregate(total=Sum('page_image_size'))['total'] or 0

    return {
        'used': used,
        'quota': USER_CACHE_QUOTA_BYTES,
        'percentage': round(used / USER_CACHE_QUOTA_BYTES * 100, 2),
        'remaining': max(0, USER_CACHE_QUOTA_BYTES - used)
    }


def get_ocr_api_key(request):
    """获取OCR API密钥（用户自带 > 平台配置）"""
    user_api_key = request.user.user_api_key if hasattr(request.user, 'user_api_key') else ''
    if user_api_key:
        return user_api_key

    platform_cfg = APIConfig.get_active()
    if platform_cfg and platform_cfg.api_key:
        return platform_cfg.api_key

    return None


# ==================== 文档项目管理 ====================

class DocumentProjectListView(APIView):
    """文档项目列表/创建"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取文档项目列表"""
        docs = DocumentProject.objects.filter(user=request.user).order_by('-updated_at')
        data = []
        for doc in docs:
            data.append({
                'id': doc.id,
                'name': doc.name,
                'file_type': doc.file_type,
                'total_pages': doc.total_pages,
                'file_size': doc.file_size,
                'cached_pages': doc.cached_pages_count,
                'cache_size': doc.cache_size_bytes,
                'cloud_file_id': doc.cloud_file_id,
                'created_at': doc.created_at.isoformat(),
                'updated_at': doc.updated_at.isoformat(),
            })
        return Response({'documents': data})

    def post(self, request):
        """创建新文档项目"""
        name = request.data.get('name', '').strip()
        file_type = request.data.get('file_type', 'pdf')
        cloud_file_id = request.data.get('cloud_file_id')
        total_pages = request.data.get('total_pages', 0)
        file_size = request.data.get('file_size', 0)

        if not name:
            return Response({'error': '文档名称不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 验证云盘文件
        cloud_file = None
        if cloud_file_id:
            from accounts.models import CloudFile
            try:
                cloud_file = CloudFile.objects.get(id=cloud_file_id, user=request.user)
            except CloudFile.DoesNotExist:
                return Response({'error': '云盘文件不存在'}, status=status.HTTP_400_BAD_REQUEST)

        doc = DocumentProject.objects.create(
            id=generate_project_id(),
            user=request.user,
            name=name,
            file_type=file_type,
            cloud_file=cloud_file,
            total_pages=total_pages,
            file_size=file_size,
        )

        return Response({
            'id': doc.id,
            'name': doc.name,
            'file_type': doc.file_type,
            'total_pages': doc.total_pages,
            'file_size': doc.file_size,
            'created_at': doc.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


class DocumentProjectDetailView(APIView):
    """文档项目详情/删除"""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        """获取文档详情"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 获取页面列表
        pages = doc.pages.all()
        page_list = []
        for p in pages:
            page_list.append({
                'page_num': p.page_num,
                'ocr_status': p.ocr_status,
                'has_image': bool(p.page_image),
                'page_width': p.page_width,
                'page_height': p.page_height,
                'cached_at': p.cached_at.isoformat() if p.cached_at else None,
            })

        return Response({
            'id': doc.id,
            'name': doc.name,
            'file_type': doc.file_type,
            'total_pages': doc.total_pages,
            'file_size': doc.file_size,
            'cached_pages': doc.cached_pages_count,
            'cache_size': doc.cache_size_bytes,
            'cloud_file_id': doc.cloud_file_id,
            'pages': page_list,
            'created_at': doc.created_at.isoformat(),
            'updated_at': doc.updated_at.isoformat(),
        })

    def delete(self, request, doc_id):
        """删除文档项目"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        doc.delete()
        return Response({'message': '文档已删除'})


# ==================== 云盘文件集成 ====================

class CloudFileListView(APIView):
    """获取用户云盘中的PDF/MD/TXT文件"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取可用的云盘文件"""
        from accounts.models import CloudFile

        file_type = request.query_params.get('type', 'pdf')
        allowed_types = {'pdf', 'md', 'txt'}

        if file_type not in allowed_types:
            file_type = 'pdf'

        files = CloudFile.objects.filter(
            user=request.user,
            file_type=file_type
        ).order_by('-uploaded_at')

        data = []
        for f in files:
            data.append({
                'id': f.id,
                'name': f.name,
                'size': f.size,
                'uploaded_at': f.uploaded_at.isoformat(),
            })

        return Response({'files': data})


# ==================== 页面缓存管理 ====================

class PageUploadView(APIView):
    """上传PDF页面渲染图片（用于OCR）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        """上传页面图片"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        page_num = request.data.get('page_num')
        image_b64 = request.data.get('image_b64', '')
        page_width = request.data.get('page_width')
        page_height = request.data.get('page_height')

        if not page_num:
            return Response({'error': '页码不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if not image_b64:
            return Response({'error': '图片数据不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查缓存配额
        cache_usage = get_user_cache_usage(request.user)
        # 估算新图片大小（base64约为原文件的4/3）
        estimated_size = len(image_b64) * 3 // 4

        if cache_usage['used'] + estimated_size > USER_CACHE_QUOTA_BYTES:
            return Response({
                'error': f'缓存空间不足（剩余 {cache_usage["remaining"] / 1024 / 1024:.1f} MB）',
                'cache_usage': cache_usage
            }, status=status.HTTP_402_PAYMENT_REQUIRED)

        # 解码base64图片
        try:
            image_data = base64.b64decode(image_b64)
        except Exception:
            return Response({'error': '图片数据格式错误'}, status=status.HTTP_400_BAD_REQUEST)

        # 保存或更新页面
        page, created = DocumentPage.objects.get_or_create(
            document=doc,
            page_num=page_num,
            defaults={
                'page_width': page_width,
                'page_height': page_height,
            }
        )

        # 保存图片
        filename = f"{page_num}.png"
        page.page_image.save(
            filename,
            ContentFile(image_data),
            save=True
        )
        page.page_image_size = page.page_image.size
        page.page_width = page_width or page.page_width
        page.page_height = page_height or page.page_height
        page.save()

        # 更新文档缓存统计
        doc.update_cache_stats()

        return Response({
            'message': '页面已缓存',
            'page_num': page.page_num,
            'size': page.page_image_size,
            'cache_usage': get_user_cache_usage(request.user),
        })


class PageDetailView(APIView):
    """获取页面详情"""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id, page_num):
        """获取页面详情和OCR结果"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
            page = DocumentPage.objects.get(document=doc, page_num=page_num)
        except (DocumentProject.DoesNotExist, DocumentPage.DoesNotExist):
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        response_data = {
            'page_num': page.page_num,
            'ocr_status': page.ocr_status,
            'page_width': page.page_width,
            'page_height': page.page_height,
            'cached_at': page.cached_at.isoformat() if page.cached_at else None,
        }

        # 如果有OCR结果，返回解析数据
        if page.ocr_status == 'done':
            try:
                response_data['layout_details'] = page.layout_details
                response_data['markdown'] = page.ocr_result_md
            except Exception:
                pass

        # 如果有错误
        if page.ocr_status == 'error':
            response_data['error_msg'] = page.error_msg

        return Response(response_data)

    def delete(self, request, doc_id, page_num):
        """删除页面缓存"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
            page = DocumentPage.objects.get(document=doc, page_num=page_num)
        except (DocumentProject.DoesNotExist, DocumentPage.DoesNotExist):
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        page.delete()
        doc.update_cache_stats()

        return Response({
            'message': '页面缓存已删除',
            'cache_usage': get_user_cache_usage(request.user),
        })


# ==================== OCR解析 ====================

class PageParseView(APIView):
    """解析单个页面（调用GLM-OCR）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id, page_num):
        """解析指定页面"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
            page = DocumentPage.objects.get(document=doc, page_num=page_num)
        except (DocumentProject.DoesNotExist, DocumentPage.DoesNotExist):
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        if not page.page_image:
            return Response({'error': '页面未缓存，请先上传页面图片'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查API密钥
        api_key = get_ocr_api_key(request)
        if not api_key:
            return Response({'error': '未配置OCR API密钥'}, status=status.HTTP_400_BAD_REQUEST)

        # 更新状态为处理中
        page.ocr_status = 'processing'
        page.save()

        # 读取图片并转为base64
        try:
            with open(page.page_image.path, 'rb') as f:
                image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
        except Exception:
            page.ocr_status = 'error'
            page.error_msg = '读取图片失败'
            page.save()
            return Response({'error': '读取图片失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 调用GLM-OCR API
        OCR_API_URL = 'https://open.bigmodel.cn/api/paas/v4/layout_parsing'
        payload = {
            "model": "glm-ocr",
            "file": f"data:image/png;base64,{image_b64}",
            "return_crop_images": False,
            "need_layout_visualization": False,
        }

        try:
            resp = requests.post(
                OCR_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=120,
            )
        except requests.RequestException as e:
            page.ocr_status = 'error'
            page.error_msg = f'网络错误: {e}'
            page.save()
            return Response({'error': f'网络错误: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if resp.status_code != 200:
            page.ocr_status = 'error'
            page.error_msg = f'OCR API错误 {resp.status_code}'
            page.save()
            return Response({'error': f'OCR API错误 {resp.status_code}'}, status=status.HTTP_502_BAD_GATEWAY)

        data = resp.json()

        # 解析结果
        md_result = data.get('md_results', '')
        layout_details = data.get('layout_details', [])

        page.ocr_status = 'done'
        page.ocr_result_raw = json.dumps(data, ensure_ascii=False)
        page.ocr_result_md = md_result
        page.layout_details = layout_details
        page.save()

        return Response({
            'message': '解析完成',
            'ocr_status': 'done',
            'markdown': md_result,
            'layout_details': layout_details,
        })


# ==================== 批量解析 ====================

class BatchParseView(APIView):
    """批量解析页面（SSE流式）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id):
        """批量解析指定页面"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        page_numbers = request.data.get('page_numbers', [])
        if not page_numbers:
            return Response({'error': '请指定要解析的页码'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查API密钥
        api_key = get_ocr_api_key(request)
        if not api_key:
            return Response({'error': '未配置OCR API密钥'}, status=status.HTTP_400_BAD_REQUEST)

        # 创建解析会话
        session = ParseSession.objects.create(
            user=request.user,
            document=doc,
            status='running',
            total_pages=len(page_numbers),
        )

        def generator():
            OCR_API_URL = 'https://open.bigmodel.cn/api/paas/v4/layout_parsing'

            for page_num in page_numbers:
                try:
                    page = DocumentPage.objects.get(document=doc, page_num=page_num)

                    if not page.page_image:
                        yield f"data: {json.dumps({'type': 'error', 'page_num': page_num, 'message': '页面未缓存'})}\n\n"
                        session.failed_pages += 1
                        session.save()
                        continue

                    # 更新状态
                    page.ocr_status = 'processing'
                    page.save()
                    yield f"data: {json.dumps({'type': 'progress', 'page_num': page_num, 'status': 'processing'})}\n\n"

                    # 读取图片
                    with open(page.page_image.path, 'rb') as f:
                        image_data = f.read()
                    image_b64 = base64.b64encode(image_data).decode('utf-8')

                    # 调用API
                    payload = {
                        "model": "glm-ocr",
                        "file": f"data:image/png;base64,{image_b64}",
                        "return_crop_images": False,
                        "need_layout_visualization": False,
                    }

                    resp = requests.post(
                        OCR_API_URL,
                        json=payload,
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        timeout=120,
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        page.ocr_status = 'done'
                        page.ocr_result_raw = json.dumps(data, ensure_ascii=False)
                        page.ocr_result_md = data.get('md_results', '')
                        page.layout_details = data.get('layout_details', [])
                        page.save()

                        session.completed_pages += 1
                        session.save()

                        yield f"data: {json.dumps({'type': 'success', 'page_num': page_num, 'markdown': page.ocr_result_md[:200] + '...' if len(page.ocr_result_md) > 200 else page.ocr_result_md})}\n\n"
                    else:
                        page.ocr_status = 'error'
                        page.error_msg = f'API错误 {resp.status_code}'
                        page.save()

                        session.failed_pages += 1
                        session.save()

                        yield f"data: {json.dumps({'type': 'error', 'page_num': page_num, 'message': page.error_msg})}\n\n"

                except DocumentPage.DoesNotExist:
                    session.failed_pages += 1
                    session.save()
                    yield f"data: {json.dumps({'type': 'error', 'page_num': page_num, 'message': '页面不存在'})}\n\n"
                except Exception as e:
                    session.failed_pages += 1
                    session.save()
                    yield f"data: {json.dumps({'type': 'error', 'page_num': page_num, 'message': str(e)})}\n\n"

            session.status = 'completed' if session.failed_pages == 0 else 'completed' if session.completed_pages > 0 else 'failed'
            session.save()

            yield f"data: {json.dumps({'type': 'done', 'total': session.total_pages, 'completed': session.completed_pages, 'failed': session.failed_pages})}\n\n"

        return StreamingHttpResponse(generator(), content_type='text/event-stream')


# ==================== 缓存配额 ====================

class CacheQuotaView(APIView):
    """获取用户缓存配额信息"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """获取缓存使用情况"""
        cache_usage = get_user_cache_usage(request.user)

        # 按文档分组的缓存详情
        docs = DocumentProject.objects.filter(user=request.user)
        doc_details = []
        for doc in docs:
            if doc.cache_size_bytes > 0:
                doc_details.append({
                    'id': doc.id,
                    'name': doc.name,
                    'cached_pages': doc.cached_pages_count,
                    'cache_size': doc.cache_size_bytes,
                })

        doc_details.sort(key=lambda x: x['cache_size'], reverse=True)

        return Response({
            'cache_usage': cache_usage,
            'documents': doc_details,
        })


# ==================== 对话管理 ====================

class ChatSessionListView(APIView):
    """对话会话列表/创建"""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id):
        """获取对话列表"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        sessions = ChatSession.objects.filter(document=doc).order_by('-updated_at')
        data = []
        for s in sessions:
            data.append({
                'id': s.id,
                'title': s.title,
                'created_at': s.created_at.isoformat(),
                'updated_at': s.updated_at.isoformat(),
            })

        return Response({'sessions': data})

    def post(self, request, doc_id):
        """创建新对话"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
        except DocumentProject.DoesNotExist:
            return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        title = request.data.get('title', '新对话')

        session = ChatSession.objects.create(
            user=request.user,
            document=doc,
            title=title,
        )

        return Response({
            'id': session.id,
            'title': session.title,
            'created_at': session.created_at.isoformat(),
        }, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    """对话会话详情"""
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id, session_id):
        """获取对话历史"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
            session = ChatSession.objects.get(id=session_id, document=doc)
        except (DocumentProject.DoesNotExist, ChatSession.DoesNotExist):
            return Response({'error': '对话不存在'}, status=status.HTTP_404_NOT_FOUND)

        messages = session.messages.all()
        data = []
        for m in messages:
            data.append({
                'id': m.id,
                'role': m.role,
                'content': m.content,
                'selected_texts': m.selected_texts,
                'instruction_type': m.instruction_type,
                'created_at': m.created_at.isoformat(),
            })

        return Response({'messages': data})


# ==================== LLM对话（流式） ====================

DOC_READER_SYSTEM_PROMPT = """你是一个专业的文档分析助手。用户会向你提供文档中的选中文本片段，并根据你的分析能力回答问题。

你的职责：
1. 翻译：将选中的文本翻译成目标语言（通常翻译成中文）
2. 总结：对选中的文本进行简洁的总结
3. 讲解：详细解释选中的内容，包括背景、含义和重要性
4. 回答问题：根据选中的文本内容回答用户的具体问题

请始终基于用户提供的文本片段进行分析，不要编造内容。
"""


class ChatStreamView(APIView):
    """流式对话端点（SSE）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id, session_id):
        """发送消息并流式返回响应"""
        try:
            doc = DocumentProject.objects.get(id=doc_id, user=request.user)
            session = ChatSession.objects.get(id=session_id, document=doc)
        except (DocumentProject.DoesNotExist, ChatSession.DoesNotExist):
            return Response({'error': '对话不存在'}, status=status.HTTP_404_NOT_FOUND)

        content = request.data.get('content', '').strip()
        selected_texts = request.data.get('selected_texts', [])
        instruction_type = request.data.get('instruction_type', 'custom')

        if not content and not selected_texts:
            return Response({'error': '请输入消息或选择文本'}, status=status.HTTP_400_BAD_REQUEST)

        # 保存用户消息
        user_msg = ChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            selected_texts=selected_texts,
            instruction_type=instruction_type,
        )

        # 更新会话时间
        session.save()

        # 构建LLM消息
        messages = []

        # 如果有选中文本，添加到上下文
        if selected_texts:
            context = "以下是用户选中的文档文本片段：\n\n"
            for i, text in enumerate(selected_texts, 1):
                context += f"[片段 {i}]\n{text}\n\n"
            messages.append({
                "role": "user",
                "content": context
            })

        # 添加当前消息
        if content:
            messages.append({
                "role": "user",
                "content": content
            })

        # 确定使用的模型
        model = 'glm-4.7-flash'  # 默认使用glm-4.7-flash
        if instruction_type == 'translate':
            model = 'glm-4-flash'  # 翻译使用glm-4-flash

        def generator():
            try:
                # 获取配置
                config = _get_config()
                # 覆盖模型
                config.chat_model = model

                full_response = ""
                for chunk in chat_stream(
                    messages=messages,
                    system=DOC_READER_SYSTEM_PROMPT,
                    project_id=None,
                    config=config,
                    user_id=request.user.id,
                ):
                    full_response += chunk
                    yield f"data: {json.dumps({'content': chunk})}\n\n"

                # 保存助手消息
                ChatMessage.objects.create(
                    session=session,
                    role='assistant',
                    content=full_response,
                    model=model,
                )

                # 更新会话时间
                session.save()

                yield f"data: {json.dumps({'done': True})}\n\n"

            except ValueError as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'生成错误: {e}'})}\n\n"

        return StreamingHttpResponse(generator(), content_type='text/event-stream')
