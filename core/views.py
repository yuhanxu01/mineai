from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import APIConfig, AgentLog


class ConfigView(APIView):
    def get(self, request):
        platform_config = APIConfig.get_active()
        platform_configured = platform_config is not None

        user_api_key = ''
        if request.user.is_authenticated:
            user_api_key = request.user.user_api_key or ''

        configured = platform_configured or bool(user_api_key)

        resp = {
            "configured": configured,
            "platform_configured": platform_configured,
            "user_key_configured": bool(user_api_key),
            "api_base": platform_config.api_base if platform_configured else 'https://open.bigmodel.cn/api/paas/v4',
            "chat_model": platform_config.chat_model if platform_configured else 'glm-4.7-flash',
        }
        if user_api_key:
            resp["api_key_preview"] = user_api_key[:8] + "..."
        elif platform_configured:
            resp["api_key_preview"] = platform_config.api_key[:8] + "..."
        else:
            resp["api_key_preview"] = ""
        return Response(resp)

    def post(self, request):
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response({'error': '权限不足，仅管理员可修改平台API配置'}, status=403)
        data = request.data
        APIConfig.objects.all().delete()
        config = APIConfig.objects.create(
            api_key=data['api_key'],
            api_base=data.get('api_base', 'https://open.bigmodel.cn/api/paas/v4'),
            chat_model=data.get('chat_model', 'glm-4.7-flash'),
        )
        return Response({"configured": True, "id": config.id})


class LogsView(APIView):
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
