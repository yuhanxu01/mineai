from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from accounts.models import User, VerificationCode, SiteConfig


@method_decorator(csrf_exempt, name='dispatch')
class UserAPIKeyView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=401)
        has_key = bool(request.user.user_api_key)
        return Response({
            'has_key': has_key,
            'preview': request.user.user_api_key[:8] + '...' if has_key else None,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=401)
        key = request.data.get('api_key', '').strip()
        if not key:
            return Response({'error': 'API密钥不能为空'}, status=400)
        request.user.user_api_key = key
        request.user.save(update_fields=['user_api_key'])
        return Response({'ok': True, 'preview': key[:8] + '...'})

    def delete(self, request):
        if not request.user.is_authenticated:
            return Response({'error': '未登录'}, status=401)
        request.user.user_api_key = ''
        request.user.save(update_fields=['user_api_key'])
        return Response({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class SendCodeView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': '邮箱不能为空'}, status=400)

        # 同一邮箱冷却检查
        remaining = VerificationCode.cooldown_remaining(email)
        if remaining > 0:
            cfg = SiteConfig.get()
            m, s = divmod(remaining, 60)
            tip = f'{m} 分 {s} 秒' if m else f'{s} 秒'
            return Response(
                {'error': f'请 {tip} 后再试', 'remaining_seconds': remaining},
                status=429,
            )

        # 全局速率限制
        ok, err = VerificationCode.check_global_limits()
        if not ok:
            return Response({'error': err}, status=429)

        code = VerificationCode.generate(email)
        cfg = SiteConfig.get()
        try:
            send_mail(
                subject='【应用平台】邮箱验证码',
                message=(
                    f'您好！\n\n'
                    f'您的注册验证码为：{code}\n\n'
                    f'验证码 {cfg.code_expire_minutes} 分钟内有效，请勿泄露给他人。\n\n'
                    f'若非本人操作，请忽略此邮件。'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'error': f'邮件发送失败，请检查邮箱是否正确（{e}）'}, status=500)

        return Response({'ok': True, 'cooldown_seconds': cfg.code_cooldown_seconds})


@method_decorator(csrf_exempt, name='dispatch')
class RegisterView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        code = request.data.get('code', '').strip()

        if not email or not password or not code:
            return Response({'error': '请填写邮箱、验证码和密码'}, status=400)
        if len(password) < 6:
            return Response({'error': '密码至少 6 位'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': '该邮箱已注册'}, status=400)
        if not VerificationCode.verify(email, code):
            return Response({'error': '验证码无效或已过期'}, status=400)

        user = User.objects.create_user(email=email, password=password)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': '邮箱或密码错误'}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email})


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    def post(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class MeView(APIView):
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'authenticated': False}, status=401)
        usage = getattr(request.user, 'token_usage', None)
        return Response({
            'authenticated': True,
            'email': request.user.email,
            'usage': {
                'prompt_count': usage.prompt_count if usage else 0,
                'input_tokens': usage.input_tokens if usage else 0,
                'output_tokens': usage.output_tokens if usage else 0,
                'total_tokens': usage.total_tokens if usage else 0,
            },
        })
