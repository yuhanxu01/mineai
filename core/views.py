import json
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from core.models import APIConfig, AgentLog


def _token_auth(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=auth[6:].strip()).user
    except Exception:
        return None


class ConfigView(APIView):
    def get(self, request):
        platform_config = APIConfig.get_active()
        platform_configured = platform_config is not None

        user_api_key = ''
        is_guest = False
        if request.user.is_authenticated:
            user_api_key = request.user.user_api_key or ''
            is_guest = getattr(request.user, 'is_guest', False)

        platform_allowed = platform_configured and request.user.is_authenticated and not is_guest
        configured = platform_allowed or bool(user_api_key)

        resp = {
            "configured": configured,
            "platform_configured": platform_configured,
            "platform_allowed": platform_allowed,
            "user_key_configured": bool(user_api_key),
            "is_guest": is_guest,
            "api_base": platform_config.api_base if platform_configured else 'https://open.bigmodel.cn/api/paas/v4',
            "chat_model": platform_config.chat_model if platform_configured else 'glm-4.7-flash',
        }
        if user_api_key:
            resp["api_key_preview"] = user_api_key[:8] + "..."
        elif platform_allowed:
            resp["api_key_preview"] = platform_config.api_key[:8] + "..."
        else:
            resp["api_key_preview"] = ""
        return Response(resp)

    def post(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response({'error': 'Insufficient permissions. Only admins can change platform API settings.'}, status=403)
        data = request.data
        APIConfig.objects.all().delete()
        config = APIConfig.objects.create(
            api_key=data['api_key'],
            api_base=data.get('api_base', 'https://open.bigmodel.cn/api/paas/v4'),
            chat_model=data.get('chat_model', 'glm-4.7-flash'),
        )
        return Response({"configured": True, "id": config.id})


class LogsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        limit = int(request.query_params.get('limit', 50))
        qs = AgentLog.objects.all()
        if project_id:
            qs = qs.filter(project_id=project_id)
        logs = qs[:limit]
        return Response([{
            "id": l.id,
            "level": l.level,
            "title": l.title,
            "content": l.content,
            "metadata": l.metadata,
            "created_at": l.created_at.isoformat(),
        } for l in logs])

    def delete(self, request):
        project_id = request.query_params.get('project_id')
        qs = AgentLog.objects.all()
        if project_id:
            qs = qs.filter(project_id=project_id)
        count = qs.count()
        qs.delete()
        return Response({"deleted": count})


@method_decorator(csrf_exempt, name='dispatch')
class SimpleChatStreamView(View):
    """
    通用流式对话接口（不绑定项目）。供悬浮聊天窗口使用。
    请求体: {"message": "...", "history": [{"role": "user/assistant", "content": "..."}]}
    """

    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({"error": "Authentication required"}, status=401)

        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({"error": "Invalid request format"}, status=400)

        message = data.get('message', '').strip()
        history = data.get('history', [])

        if not message:
            return JsonResponse({"error": "Message is required"}, status=400)

        messages = [
            {'role': m['role'], 'content': m['content']}
            for m in history[-20:]
            if m.get('role') in ('user', 'assistant') and m.get('content')
        ]
        messages.append({'role': 'user', 'content': message})

        from core.llm import _get_config, _check_quota, chat_stream
        try:
            config = _get_config()
            _check_quota(user.id, config)
        except ValueError as e:
            return JsonResponse({"error": str(e)}, status=429)

        user_id = user.id

        def generate():
            try:
                for chunk in chat_stream(
                    messages,
                    system="You are a smart AI assistant that helps answer a wide range of questions. Reply concisely and clearly.",
                    temperature=0.7, max_tokens=2048,
                    config=config, user_id=user_id,
                ):
                    yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp
