from core.context import set_user


class UserContextMiddleware:
    """从请求头读取 Token，将用户ID写入线程局部变量，供 llm.py 跟踪用量。"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_user(None)
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Token '):
            token_key = auth_header[6:].strip()
            try:
                from rest_framework.authtoken.models import Token
                token = Token.objects.select_related('user').get(key=token_key)
                set_user(token.user_id)
            except Exception:
                pass
        try:
            response = self.get_response(request)
        finally:
            set_user(None)
        return response
