def _token_auth(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=auth[6:].strip()).user
    except Exception:
        return None
