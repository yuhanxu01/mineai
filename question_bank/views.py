"""
AI 题库后端视图
- 普通 CRUD 端点使用 DRF APIView + TokenAuthentication
- 流式 SSE 端点使用 @csrf_exempt + _token_auth 手动鉴权
"""
import json
import urllib.request
import urllib.error
import requests

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny

from core.views import _token_auth
from core.models import APIConfig, AgentLog

from .models import (
    Question, ChatMessage, FinalAnswer, StandardAnswer,
    SharedQuestion, Comment, Like, Favorite,
)

OCR_API_URL = 'https://open.bigmodel.cn/api/paas/v4/images/recognition'
VISION_MODEL = 'glm-4v-flash'
TEXT_MODEL = 'glm-4.7-flash'


# ── 工具函数 ───────────────────────────────────────────────────────────────

def _get_api_config(user=None):
    """取 APIConfig；用户有自带 key 时优先使用。"""
    if user and getattr(user, 'user_api_key', None):
        cfg = APIConfig.get_active()
        api_base = cfg.api_base if cfg else 'https://open.bigmodel.cn/api/paas/v4'
        return {'api_key': user.user_api_key, 'api_base': api_base}
    cfg = APIConfig.get_active()
    if not cfg:
        raise ValueError('Platform API is not configured. Please contact an admin or set your own API key.')
    return {'api_key': cfg.api_key, 'api_base': cfg.api_base}


def _glm_chat_stream(messages, model, api_key, api_base, project_id=None, user_id=None):
    """
    向 GLM API 发起流式请求，逐块 yield 文本内容。
    messages: list of {"role": str, "content": str | list}
    """
    url = f'{api_base}/chat/completions'
    payload = {
        'model': model,
        'messages': messages,
        'temperature': 0.7,
        'max_tokens': 4096,
        'stream': True,
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}',
    })
    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'题库·流式调用 {model}',
        content=str(messages[-1].get('content', ''))[:200] if messages else '',
        metadata={'model': model, 'stream': True},
    )
    usage = {}
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode('utf-8').strip()
                if not line or not line.startswith('data: '):
                    continue
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                try:
                    chunk = json.loads(data_str)
                    delta = chunk['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        yield content
                    if chunk.get('usage'):
                        usage = chunk['usage']
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        raise ValueError(f'GLM API error {e.code}: {body}')

    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'题库·流式完成 ({usage.get("total_tokens", "?")} tokens)',
        content='',
        metadata=usage,
    )
    if user_id and usage:
        try:
            from accounts.models import TokenUsage
            TokenUsage.record(user_id, usage)
        except Exception:
            pass


def _question_to_dict(q, user=None):
    d = {
        'id': q.id,
        'title': q.title,
        'content': q.content,
        'model_used': q.model_used,
        'status': q.status,
        'tags': q.tags,
        'subject': q.subject,
        'has_image': bool(q.original_image),
        'image_type': q.image_type,
        'created_at': q.created_at.isoformat(),
        'updated_at': q.updated_at.isoformat(),
        'has_final_answer': hasattr(q, 'final_answer'),
        'has_standard_answer': hasattr(q, 'standard_answer'),
        'is_published': hasattr(q, 'shared'),
    }
    if d['has_image']:
        d['image_data_url'] = f'data:image/{q.image_type or "jpeg"};base64,{q.original_image}'
    return d


def _shared_to_dict(sq, user=None):
    q = sq.question
    d = {
        'id': sq.id,
        'question_id': q.id,
        'title': q.title,
        'content': q.content,
        'subject': q.subject,
        'tags': q.tags,
        'model_used': q.model_used,
        'has_image': bool(q.original_image),
        'image_type': q.image_type,
        'author': q.user.email if not q.user.is_staff else '管理员',
        'published_at': sq.published_at.isoformat(),
        'view_count': sq.view_count,
        'like_count': sq.like_count(),
        'favorite_count': sq.favorite_count(),
        'comment_count': sq.comment_count(),
        'liked': False,
        'favorited': False,
    }
    if d['has_image']:
        d['image_data_url'] = f'data:image/{q.image_type or "jpeg"};base64,{q.original_image}'
    try:
        fa = q.final_answer
        d['final_answer'] = fa.content
    except FinalAnswer.DoesNotExist:
        d['final_answer'] = ''
    try:
        sa = q.standard_answer
        d['standard_answer_md'] = sa.content_md
        d['standard_answer_image'] = (
            f'data:image/{sa.image_type or "jpeg"};base64,{sa.image}'
            if sa.image else ''
        )
    except StandardAnswer.DoesNotExist:
        d['standard_answer_md'] = ''
        d['standard_answer_image'] = ''
    if user and user.is_authenticated:
        d['liked'] = Like.objects.filter(shared_question=sq, user=user).exists()
        d['favorited'] = Favorite.objects.filter(shared_question=sq, user=user).exists()
    return d


# ── OCR 端点 ────────────────────────────────────────────────────────────────

class OCRView(APIView):
    """POST image_b64 → OCR 识别文本。"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image_b64 = request.data.get('image_b64', '').strip()
        image_type = request.data.get('image_type', 'jpeg').strip()
        api_key_override = request.data.get('api_key', '').strip()

        if not image_b64:
            return Response({'error': 'Please provide image data'}, status=400)

        try:
            cfg = _get_api_config(request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)

        key = api_key_override or cfg['api_key']
        ocr_url = f"{cfg['api_base']}/images/recognition"

        payload = {
            'model': 'glm-ocr',
            'file': f'data:image/{image_type};base64,{image_b64}',
        }
        try:
            resp = requests.post(
                ocr_url,
                json=payload,
                headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
                timeout=120,
            )
        except requests.RequestException as e:
            return Response({'error': f'Network error: {e}'}, status=503)

        if resp.status_code != 200:
            return Response(
                {'error': f'OCR API error {resp.status_code}: {resp.text[:300]}'},
                status=502,
            )

        data = resp.json()
        text = (
            data.get('md_results', '')
            or data.get('data', {}).get('md_results', '')
            or data.get('data', {}).get('content', '')
            or data.get('content', '')
        )
        if not text and 'choices' in data:
            text = data['choices'][0].get('message', {}).get('content', '')
        return Response({'text': text or str(data)})


# ── 题目 CRUD ────────────────────────────────────────────────────────────────

class QuestionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Question.objects.filter(user=request.user).prefetch_related(
            'final_answer', 'standard_answer', 'shared'
        )
        return Response([_question_to_dict(q) for q in qs])

    def post(self, request):
        title = request.data.get('title', '').strip()
        content = request.data.get('content', '').strip()
        original_image = request.data.get('original_image', '').strip()
        image_type = request.data.get('image_type', 'jpeg').strip()
        model_used = request.data.get('model_used', TEXT_MODEL).strip()
        tags = request.data.get('tags', '').strip()
        subject = request.data.get('subject', '').strip()

        q = Question.objects.create(
            user=request.user,
            title=title or content[:60] or 'New question',
            content=content,
            original_image=original_image,
            image_type=image_type,
            model_used=model_used,
            tags=tags,
            subject=subject,
        )
        return Response(_question_to_dict(q), status=201)


class QuestionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_question(self, pk, user):
        try:
            return Question.objects.get(pk=pk, user=user)
        except Question.DoesNotExist:
            return None

    def get(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        d = _question_to_dict(q)
        if q.original_image:
            d['original_image'] = q.original_image
        d['messages'] = [
            {
                'role': m.role,
                'content': m.content,
                'model_used': m.model_used,
                'created_at': m.created_at.isoformat(),
            }
            for m in q.messages.all()
        ]
        try:
            d['final_answer_content'] = q.final_answer.content
        except FinalAnswer.DoesNotExist:
            d['final_answer_content'] = ''
        try:
            sa = q.standard_answer
            d['standard_answer_md'] = sa.content_md
            d['standard_answer_image'] = (
                f'data:image/{sa.image_type or "jpeg"};base64,{sa.image}'
                if sa.image else ''
            )
        except StandardAnswer.DoesNotExist:
            d['standard_answer_md'] = ''
            d['standard_answer_image'] = ''
        return Response(d)

    def put(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        for field in ('title', 'content', 'model_used', 'tags', 'subject'):
            if field in request.data:
                setattr(q, field, request.data[field])
        if 'original_image' in request.data:
            q.original_image = request.data['original_image']
            q.image_type = request.data.get('image_type', q.image_type)
        q.save()
        return Response(_question_to_dict(q))

    def delete(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        q.delete()
        return Response(status=204)


# ── 流式 AI 对话 ─────────────────────────────────────────────────────────────

@csrf_exempt
def chat_stream_view(request, pk):
    """
    POST /api/qbank/questions/<pk>/chat-stream/
    Body: {message, model, include_image (bool)}
    SSE: data: {"content": "..."}  /  data: {"done": true}
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    user = _token_auth(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    try:
        q = Question.objects.get(pk=pk, user=user)
    except Question.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    user_message = body.get('message', '').strip()
    model = body.get('model', q.model_used or TEXT_MODEL)
    include_image = body.get('include_image', False)

    if not user_message:
        return JsonResponse({'error': 'Message cannot be empty'}, status=400)

    # 更新题目当前使用的模型
    if model != q.model_used:
        q.model_used = model
        q.save(update_fields=['model_used'])

    try:
        cfg = _get_api_config(user)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    # 构建消息历史
    history = list(q.messages.all().order_by('created_at'))
    api_messages = []

    for msg in history:
        api_messages.append({'role': msg.role, 'content': msg.content})

    # 当前用户消息：如果是视觉模型且题目有图片，首次消息带图
    is_vision = model == VISION_MODEL
    if is_vision and include_image and q.original_image and len(history) == 0:
        user_content = [
            {'type': 'text', 'text': user_message},
            {'type': 'image_url', 'image_url': {
                'url': f'data:image/{q.image_type or "jpeg"};base64,{q.original_image}'
            }},
        ]
    else:
        user_content = user_message

    api_messages.append({'role': 'user', 'content': user_content})

    # 保存用户消息（存文本）
    ChatMessage.objects.create(
        question=q,
        role='user',
        content=user_message,
        model_used=model,
    )

    user_id = user.id

    def generator():
        full_response = []
        try:
            for chunk in _glm_chat_stream(
                api_messages, model,
                cfg['api_key'], cfg['api_base'],
                project_id=None, user_id=user_id,
            ):
                full_response.append(chunk)
                yield f'data: {json.dumps({"content": chunk})}\n\n'
        except ValueError as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
            return

        ai_text = ''.join(full_response)
        ChatMessage.objects.create(
            question=q,
            role='assistant',
            content=ai_text,
            model_used=model,
        )
        yield f'data: {json.dumps({"done": True})}\n\n'

    return StreamingHttpResponse(generator(), content_type='text/event-stream')


# ── 最终答案 ─────────────────────────────────────────────────────────────────

class FinalAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_question(self, pk, user):
        try:
            return Question.objects.get(pk=pk, user=user)
        except Question.DoesNotExist:
            return None

    def get(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        try:
            return Response({'content': q.final_answer.content})
        except FinalAnswer.DoesNotExist:
            return Response({'content': ''})

    def post(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        content = request.data.get('content', '').strip()
        fa, _ = FinalAnswer.objects.update_or_create(
            question=q, defaults={'content': content}
        )
        return Response({'content': fa.content})


# ── 标准答案 ─────────────────────────────────────────────────────────────────

class StandardAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_question(self, pk, user):
        try:
            return Question.objects.get(pk=pk, user=user)
        except Question.DoesNotExist:
            return None

    def get(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        try:
            sa = q.standard_answer
            return Response({
                'content_md': sa.content_md,
                'image': f'data:image/{sa.image_type or "jpeg"};base64,{sa.image}' if sa.image else '',
            })
        except StandardAnswer.DoesNotExist:
            return Response({'content_md': '', 'image': ''})

    def post(self, request, pk):
        q = self._get_question(pk, request.user)
        if not q:
            return Response({'error': 'Not found'}, status=404)
        content_md = request.data.get('content_md', '').strip()
        image = request.data.get('image', '').strip()
        image_type = request.data.get('image_type', 'jpeg').strip()
        sa, _ = StandardAnswer.objects.update_or_create(
            question=q,
            defaults={'content_md': content_md, 'image': image, 'image_type': image_type},
        )
        return Response({
            'content_md': sa.content_md,
            'image': f'data:image/{sa.image_type or "jpeg"};base64,{sa.image}' if sa.image else '',
        })


# ── 发布到共享题库 ────────────────────────────────────────────────────────────

class PublishView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            q = Question.objects.get(pk=pk, user=request.user)
        except Question.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        if not q.content.strip() and not q.original_image:
            return Response({'error': 'Question content cannot be empty'}, status=400)

        sq, created = SharedQuestion.objects.get_or_create(question=q)
        q.status = Question.STATUS_PUBLISHED
        q.save(update_fields=['status'])
        return Response({
            'shared_id': sq.id,
            'created': created,
            'message': 'Published successfully' if created else 'Shared question updated',
        })

    def delete(self, request, pk):
        try:
            q = Question.objects.get(pk=pk, user=request.user)
            SharedQuestion.objects.filter(question=q).delete()
            q.status = Question.STATUS_DRAFT
            q.save(update_fields=['status'])
            return Response({'message': 'Unpublished'})
        except Question.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)


# ── 共享题库 ─────────────────────────────────────────────────────────────────

class SharedListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        search = request.query_params.get('q', '').strip()
        subject = request.query_params.get('subject', '').strip()
        qs = SharedQuestion.objects.select_related('question', 'question__user').order_by('-published_at')
        if search:
            qs = qs.filter(question__title__icontains=search) | qs.filter(question__content__icontains=search)
            qs = qs.distinct()
        if subject:
            qs = qs.filter(question__subject__icontains=subject)
        user = request.user if request.user.is_authenticated else None
        return Response([_shared_to_dict(sq, user) for sq in qs[:100]])


class SharedDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, pk):
        try:
            sq = SharedQuestion.objects.select_related('question', 'question__user').get(pk=pk)
        except SharedQuestion.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        sq.view_count += 1
        sq.save(update_fields=['view_count'])
        user = request.user if request.user.is_authenticated else None
        d = _shared_to_dict(sq, user)
        d['comments'] = [
            {
                'id': c.id,
                'user': c.user.email,
                'content': c.content,
                'created_at': c.created_at.isoformat(),
            }
            for c in sq.comments.select_related('user').all()
        ]
        return Response(d)


class CommentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sq = SharedQuestion.objects.get(pk=pk)
        except SharedQuestion.DoesNotExist:
            return Response({'error': '未找到'}, status=404)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Comment cannot be empty'}, status=400)
        c = Comment.objects.create(shared_question=sq, user=request.user, content=content)
        return Response({
            'id': c.id,
            'user': request.user.email,
            'content': c.content,
            'created_at': c.created_at.isoformat(),
        }, status=201)


class LikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sq = SharedQuestion.objects.get(pk=pk)
        except SharedQuestion.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        like, created = Like.objects.get_or_create(shared_question=sq, user=request.user)
        if not created:
            like.delete()
            return Response({'liked': False, 'count': sq.like_count()})
        return Response({'liked': True, 'count': sq.like_count()})


class FavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            sq = SharedQuestion.objects.get(pk=pk)
        except SharedQuestion.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        fav, created = Favorite.objects.get_or_create(shared_question=sq, user=request.user)
        if not created:
            fav.delete()
            return Response({'favorited': False, 'count': sq.favorite_count()})
        return Response({'favorited': True, 'count': sq.favorite_count()})
