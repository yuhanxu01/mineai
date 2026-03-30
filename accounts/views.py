import os
import uuid
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.http import FileResponse, Http404
from django.utils.text import get_valid_filename
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated

import json
from django.utils import timezone
from accounts.models import (
    User, VerificationCode, SiteConfig, PasswordResetToken,
    CloudFile, ALLOWED_EXTENSIONS, ALLOWED_MIME_PREFIXES,
    EXT_TO_TYPE, sha256_of_file, CLOUD_QUOTA_BYTES,
    DonationRecord,
)


class SiteConfigPublicView(APIView):
    """公开接口：返回网站品牌配置，无需认证。"""
    permission_classes = [AllowAny]

    def get(self, request):
        cfg = SiteConfig.get()
        return Response({
            'site_title': cfg.site_title,
            'site_subtitle': cfg.site_subtitle,
            'site_favicon': cfg.site_favicon,
        })


@method_decorator(csrf_exempt, name='dispatch')
class UserAPIKeyView(APIView):
    permission_classes = [IsAuthenticated]
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
    permission_classes = [AllowAny]

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
                subject='【MineAI】邮箱验证码',
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
    permission_classes = [AllowAny]

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
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({'error': '邮箱或密码错误'}, status=401)
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email})


@method_decorator(csrf_exempt, name='dispatch')
class GuestLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated and getattr(request.user, 'is_guest', False):
            token, _ = Token.objects.get_or_create(user=request.user)
            return Response({'token': token.key, 'email': request.user.email, 'is_guest': True})

        # Create a new guest user (no password, cannot login with email)
        guest_email = f"guest-{uuid.uuid4().hex}@guest.local"
        user = User(email=guest_email, is_guest=True)
        user.set_unusable_password()
        user.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key, 'email': user.email, 'is_guest': True})


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    permission_classes = [AllowAny]  # 未登录也可调用，内部会安全处理

    def post(self, request):
        if request.user.is_authenticated:
            Token.objects.filter(user=request.user).delete()
        return Response({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': '邮箱不能为空'}, status=400)

        # 不暴露邮箱是否存在
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'ok': True})

        token = PasswordResetToken.objects.create(user=user)
        reset_url = f"{settings.SITE_URL}/#/reset-password?token={token.token}"

        try:
            send_mail(
                subject='【MineAI】密码重置',
                message=(
                    f'您好！\n\n'
                    f'请点击以下链接重置您的密码（30 分钟内有效）：\n\n'
                    f'{reset_url}\n\n'
                    f'若非本人操作，请忽略此邮件。'
                ),
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'error': f'邮件发送失败（{e}）'}, status=500)

        return Response({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token_str = request.data.get('token', '').strip()
        new_password = request.data.get('password', '')

        if not token_str or not new_password:
            return Response({'error': '参数不完整'}, status=400)
        if len(new_password) < 6:
            return Response({'error': '密码至少 6 位'}, status=400)

        try:
            token = PasswordResetToken.objects.select_related('user').get(token=token_str)
        except (PasswordResetToken.DoesNotExist, ValueError):
            return Response({'error': '链接无效或已过期'}, status=400)

        if not token.is_valid():
            return Response({'error': '链接已过期或已使用，请重新申请'}, status=400)

        token.user.set_password(new_password)
        token.user.save(update_fields=['password'])
        token.is_used = True
        token.save(update_fields=['is_used'])
        # 使所有登录 token 失效，强制重新登录
        Token.objects.filter(user=token.user).delete()

        return Response({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class MeView(APIView):
    permission_classes = [AllowAny]  # 内部用 is_authenticated 判断，未登录返回 authenticated:false

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'authenticated': False}, status=401)
        usage = getattr(request.user, 'token_usage', None)
        cfg = SiteConfig.get()
        has_own_key = bool(request.user.user_api_key)
        is_guest = getattr(request.user, 'is_guest', False)
        used_bytes = 0 if is_guest else request.user.cloud_used_bytes
        return Response({
            'authenticated': True,
            'email': request.user.email,
            'is_guest': is_guest,
            'is_staff': request.user.is_staff,
            'has_own_key': has_own_key,
            'joined': request.user.created_at.strftime('%Y-%m-%d') if request.user.created_at else None,
            'points': round(request.user.points, 4) if not is_guest else 0,
            'pending_donations': DonationRecord.objects.filter(user=request.user, status='pending').count() if not is_guest else 0,
            'usage': {
                'prompt_count': usage.prompt_count if usage else 0,
                'input_tokens': usage.input_tokens if usage else 0,
                'output_tokens': usage.output_tokens if usage else 0,
                'total_tokens': usage.total_tokens if usage else 0,
                'daily_prompt_count': usage.daily_prompt_count if usage else 0,
                'daily_input_tokens': usage.daily_input_tokens if usage else 0,
                'daily_output_tokens': usage.daily_output_tokens if usage else 0,
            },
            'quota': None if (has_own_key or request.user.is_staff or is_guest) else {
                'daily_prompt_count': cfg.free_daily_prompt_count,
                'daily_input_tokens': cfg.free_daily_input_tokens,
                'daily_output_tokens': cfg.free_daily_output_tokens,
            },
            'cloud': {
                'used_bytes': used_bytes,
                'quota_bytes': CLOUD_QUOTA_BYTES,
            },
        })


# ─── Cloud Drive ──────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class CloudListUploadView(APIView):
    """GET: list user files. POST: upload a new file."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.is_guest:
            return Response({'error': '访客无法使用云盘'}, status=403)
        files = request.user.cloud_files.all()
        data = []
        for f in files:
            data.append({
                'id': f.id,
                'name': f.name,
                'size': f.size,
                'file_type': f.file_type,
                'uploaded_at': f.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            })
        return Response({
            'files': data,
            'used_bytes': request.user.cloud_used_bytes,
            'quota_bytes': CLOUD_QUOTA_BYTES,
        })

    def post(self, request):
        if request.user.is_guest:
            return Response({'error': '请先登录以使用云盘'}, status=403)

        uploaded = request.FILES.get('file')
        if not uploaded:
            return Response({'error': '未选择文件'}, status=400)

        # --- extension check ---
        _, ext = os.path.splitext(uploaded.name.lower())
        if ext not in ALLOWED_EXTENSIONS:
            return Response({'error': f'不支持的文件类型 {ext}，请上传 PDF、图片、文档或代码文件'}, status=400)

        # --- MIME check ---
        mime = uploaded.content_type or ''
        if not any(mime.startswith(p) for p in ALLOWED_MIME_PREFIXES):
            # fallback: still allow if extension is in whitelist
            if ext not in ALLOWED_EXTENSIONS:
                return Response({'error': f'不允许上传此类型文件（{mime}）'}, status=400)

        # --- size check ---
        file_size = uploaded.size
        if file_size > 10 * 1024 * 1024:  # 10 MB single file limit
            return Response({'error': '单个文件不能超过 10 MB'}, status=400)

        used = request.user.cloud_used_bytes
        if used + file_size > CLOUD_QUOTA_BYTES:
            remaining = max(0, CLOUD_QUOTA_BYTES - used)
            return Response({'error': f'云盘空间不足，剩余 {remaining / 1024 / 1024:.1f} MB'}, status=400)

        # --- compute sha256 ---
        file_hash = sha256_of_file(uploaded)

        # --- sanitize filename ---
        safe_name = get_valid_filename(uploaded.name)[:200]

        file_type = EXT_TO_TYPE.get(ext, 'other')
        cloud_file = CloudFile(
            user=request.user,
            name=safe_name,
            size=file_size,
            file_type=file_type,
            sha256=file_hash,
        )
        cloud_file.file = uploaded
        cloud_file.save()

        return Response({
            'id': cloud_file.id,
            'name': cloud_file.name,
            'size': cloud_file.size,
            'file_type': cloud_file.file_type,
            'uploaded_at': cloud_file.uploaded_at.strftime('%Y-%m-%d %H:%M'),
            'used_bytes': request.user.cloud_used_bytes,
            'quota_bytes': CLOUD_QUOTA_BYTES,
        }, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class CloudFileDetailView(APIView):
    """DELETE: delete a cloud file."""
    permission_classes = [IsAuthenticated]

    def _get_obj(self, request, pk):
        try:
            return request.user.cloud_files.get(pk=pk)
        except CloudFile.DoesNotExist:
            return None

    def delete(self, request, pk):
        if request.user.is_guest:
            return Response({'error': '请先登录'}, status=403)
        obj = self._get_obj(request, pk)
        if not obj:
            return Response({'error': '文件不存在'}, status=404)
        # delete the actual file from storage
        if obj.file and default_storage.exists(obj.file.name):
            default_storage.delete(obj.file.name)
        obj.delete()
        return Response({'ok': True, 'used_bytes': request.user.cloud_used_bytes})


@method_decorator(csrf_exempt, name='dispatch')
class CloudFileDownloadView(APIView):
    """GET: serve / download a cloud file."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        if request.user.is_guest:
            return Response({'error': '请先登录'}, status=403)
        try:
            obj = request.user.cloud_files.get(pk=pk)
        except CloudFile.DoesNotExist:
            raise Http404
        if not obj.file or not default_storage.exists(obj.file.name):
            raise Http404
        response = FileResponse(
            default_storage.open(obj.file.name, 'rb'),
            as_attachment=True,
            filename=obj.name,
        )
        return response


# ─── Admin: User Management ──────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class AdminUserListView(APIView):
    """GET /api/auth/admin/users/?q=email — 管理员搜索用户（仅 staff）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': '无权限'}, status=403)
        q = request.query_params.get('q', '').strip()
        qs = User.objects.filter(is_guest=False).order_by('-created_at')
        if q:
            qs = qs.filter(email__icontains=q)
        qs = qs[:50]
        data = []
        for u in qs:
            usage = getattr(u, 'token_usage', None)
            data.append({
                'id': u.id,
                'email': u.email,
                'is_staff': u.is_staff,
                'is_active': u.is_active,
                'joined': u.created_at.strftime('%Y-%m-%d') if u.created_at else None,
                'points': round(u.points, 4),
                'total_tokens': usage.total_tokens if usage else 0,
                'has_own_key': bool(u.user_api_key),
            })
        return Response({'users': data, 'count': len(data)})


@method_decorator(csrf_exempt, name='dispatch')
class AdminUserPointsView(APIView):
    """POST /api/auth/admin/users/<pk>/points/ — 管理员为用户充值积分（仅 staff）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': '无权限'}, status=403)
        try:
            target = User.objects.get(pk=pk)
        except User.DoesNotExist:
            return Response({'error': '用户不存在'}, status=404)
        delta = request.data.get('delta')
        try:
            delta = float(delta)
        except (TypeError, ValueError):
            return Response({'error': 'delta 必须为数字'}, status=400)
        target.points = max(0.0, target.points + delta)
        target.save(update_fields=['points'])
        return Response({
            'ok': True,
            'email': target.email,
            'points': round(target.points, 4),
            'delta': delta,
        })


# ─── Donation Claim & Review ─────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class DonationClaimView(APIView):
    """POST /api/auth/donate/claim/ — 用户提交赞赏申请（已登录用户）"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.is_guest:
            return Response({'error': '请先登录'}, status=403)
        note = request.data.get('note', '').strip()[:200]
        # 检查是否有太多待审核的记录（防刷）
        pending_count = DonationRecord.objects.filter(user=request.user, status='pending').count()
        if pending_count >= 5:
            return Response({'error': '您已有 5 条待审核记录，请等待管理员处理后再提交'}, status=429)
        # 解析金额：note 格式为 "邮箱 | 金额: 6元"
        amount_points = 10.0  # 默认值
        try:
            import re
            match = re.search(r'金额[:\s]*([\d.]+)\s*元', note)
            if match:
                amount_cny = float(match.group(1))
                # 1元 = 10积分
                amount_points = round(amount_cny * 10, 2)
        except:
            pass  # 解析失败时使用默认值
        
        record = DonationRecord.objects.create(
            user=request.user,
            amount_points=amount_points,
            note=note,
            status='pending',
        )
        return Response({
            'ok': True,
            'id': record.id,
            'amount_points': record.amount_points,
            'status': record.status,
            'created_at': record.created_at.strftime('%Y-%m-%d %H:%M'),
        }, status=201)

    def get(self, request):
        """GET: 查看自己的赞赏记录"""
        if request.user.is_guest:
            return Response({'records': []})
        records = DonationRecord.objects.filter(user=request.user).order_by('-created_at')[:20]
        data = [{
            'id': r.id,
            'amount_points': r.amount_points,
            'note': r.note,
            'status': r.status,
            'status_display': r.get_status_display(),
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
            'reviewed_at': r.reviewed_at.strftime('%Y-%m-%d %H:%M') if r.reviewed_at else None,
            'reviewer_note': r.reviewer_note,
        } for r in records]
        return Response({'records': data})


@method_decorator(csrf_exempt, name='dispatch')
class AdminDonationListView(APIView):
    """GET /api/auth/admin/donations/ — 管理员查看赞赏记录"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not request.user.is_staff:
            return Response({'error': '无权限'}, status=403)
        status_filter = request.query_params.get('status', 'pending')
        qs = DonationRecord.objects.select_related('user').filter(status=status_filter).order_by('-created_at')[:100]
        data = [{
            'id': r.id,
            'user_id': r.user_id,
            'email': r.user.email,
            'amount_points': r.amount_points,
            'note': r.note,
            'status': r.status,
            'status_display': r.get_status_display(),
            'created_at': r.created_at.strftime('%Y-%m-%d %H:%M'),
        } for r in qs]
        pending_count = DonationRecord.objects.filter(status='pending').count()
        return Response({'records': data, 'pending_count': pending_count})


@method_decorator(csrf_exempt, name='dispatch')
class AdminDonationReviewView(APIView):
    """POST /api/auth/admin/donations/<pk>/review/ — 管理员审批赞赏"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not request.user.is_staff:
            return Response({'error': '无权限'}, status=403)
        try:
            record = DonationRecord.objects.select_related('user').get(pk=pk)
        except DonationRecord.DoesNotExist:
            return Response({'error': '记录不存在'}, status=404)
        if record.status != 'pending':
            return Response({'error': '该记录已处理'}, status=400)
        action = request.data.get('action')  # 'approve' | 'reject'
        if action not in ('approve', 'reject'):
            return Response({'error': 'action 必须为 approve 或 reject'}, status=400)
        reviewer_note = request.data.get('reviewer_note', '').strip()[:200]
        record.status = 'approved' if action == 'approve' else 'rejected'
        record.reviewed_at = timezone.now()
        record.reviewer_note = reviewer_note
        record.save(update_fields=['status', 'reviewed_at', 'reviewer_note'])
        if action == 'approve':
            user = record.user
            user.points = user.points + record.amount_points
            user.save(update_fields=['points'])
        return Response({
            'ok': True,
            'status': record.status,
            'user_email': record.user.email,
            'points_granted': record.amount_points if action == 'approve' else 0,
        })
