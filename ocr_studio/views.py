import io
import json
import uuid
import redis
import requests

from PIL import Image

from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import OCRProject, OCRPage, OCRUsageQuota


# ─────────────────────────────────────────────────────────────
# 工具函数
# ─────────────────────────────────────────────────────────────

OCR_API_URL = 'https://api.z.ai/api/paas/v4/layout_parsing'
MAX_B64_SIZE = 40 * 1024 * 1024
MAX_EDGE = 512          # 上传图片最大边分辨率
JPEG_QUALITY = 50       # JPEG 压缩质量


def _generate_project_id():
    """生成 12 位随机项目 ID"""
    return uuid.uuid4().hex[:12]


def _get_redis():
    """获取 Redis 连接"""
    return redis.Redis(
        host=getattr(settings, 'REDIS_HOST', 'localhost'),
        port=getattr(settings, 'REDIS_PORT', 6379),
        db=getattr(settings, 'REDIS_DB', 0),
        decode_responses=True
    )


def _generate_callback_token():
    return str(uuid.uuid4())


def _process_image(image_file, is_binary=False):
    """
    对上传图片进行预处理：
    - 将最大边缩放至不超过 MAX_EDGE (512)
    - 普通图片：转 JPEG 50% 压缩
    - 二值化图片：转 P 模式 PNG
    返回 (ContentFile, filename)
    """
    img = Image.open(image_file)

    # 缩放
    w, h = img.size
    if max(w, h) > MAX_EDGE:
        ratio = MAX_EDGE / max(w, h)
        img = img.resize((int(w * ratio), int(h * ratio)), Image.LANCZOS)

    buf = io.BytesIO()
    if is_binary:
        gray = img.convert('L')
        p_img = gray.convert('P')
        p_img.save(buf, format='PNG', optimize=True)
        filename = 'processed.png'
    else:
        rgb = img.convert('RGB')
        rgb.save(buf, format='JPEG', quality=JPEG_QUALITY, optimize=True)
        filename = 'processed.jpg'

    buf.seek(0)
    return ContentFile(buf.read(), name=filename), filename


def _get_or_update_quota(user, delta_upload=0, delta_like=0, delta_dislike=0,
                         delta_nonfeedback=0, delta_edit=0):
    """获取或更新用户今日配额，返回 quota 对象"""
    quota, _ = OCRUsageQuota.objects.get_or_create(
        user=user,
        quota_date=timezone.now().date(),
        defaults={
            'upload_count': 0,
            'like_count': 0,
            'dislike_count': 0,
            'edit_count': 0,
            'nonfeedback_count': 0,
        }
    )
    if delta_upload:
        quota.upload_count += delta_upload
    if delta_like:
        quota.like_count += delta_like
    if delta_dislike:
        quota.dislike_count += delta_dislike
    if delta_edit:
        quota.edit_count += delta_edit
    if delta_nonfeedback:
        quota.nonfeedback_count += delta_nonfeedback
    quota.save()
    return quota


def _check_worker_token(request):
    """
    Optional shared token auth for OCR worker endpoints.
    If OCR_WORKER_TOKEN is empty, keep backward compatibility.
    """
    expected = (getattr(settings, 'OCR_WORKER_TOKEN', '') or '').strip()
    if not expected:
        return None

    provided = (
        request.headers.get('X-OCR-Worker-Token', '')
        or request.META.get('HTTP_X_OCR_WORKER_TOKEN', '')
        or request.GET.get('worker_token', '')
        or request.data.get('worker_token', '')
    ).strip()

    if not provided:
        auth = (request.headers.get('Authorization', '') or '').strip()
        if auth.startswith('Bearer '):
            provided = auth[7:].strip()

    if provided != expected:
        return Response({'error': '无效的 worker 凭证'}, status=status.HTTP_401_UNAUTHORIZED)
    return None


# ─────────────────────────────────────────────────────────────
# 直连 API 模式（保留）
# ─────────────────────────────────────────────────────────────

class OCRRecognizeView(APIView):
    """
    浏览器端把页面渲染成 base64 PNG，POST 到这里，
    后端转发给 OCR API 并把结果原样返回。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image_b64 = request.data.get('image_b64', '')
        api_key = request.data.get('api_key', '').strip()
        prompt = request.data.get('prompt', '').strip()

        if not image_b64:
            return Response({'error': '请提供图片数据'}, status=status.HTTP_400_BAD_REQUEST)
        if len(image_b64) > MAX_B64_SIZE:
            return Response({'error': '图片过大（>30 MB），请降低分辨率后重试'},
                            status=status.HTTP_400_BAD_REQUEST)

        if not api_key:
            if getattr(request.user, 'is_guest', False):
                return Response({'error': '访客用户请填写自己的 OCR API 密钥'}, status=status.HTTP_400_BAD_REQUEST)
            from core.models import APIConfig
            platform_cfg = APIConfig.get_active()
            if not platform_cfg or not platform_cfg.api_key:
                return Response({'error': '平台 OCR API 未配置，请填写自己的密钥'}, status=status.HTTP_400_BAD_REQUEST)
            api_key = platform_cfg.api_key

        payload = {"model": "glm-ocr", "file": f"data:image/png;base64,{image_b64}"}
        if prompt:
            payload["prompt"] = prompt

        try:
            resp = requests.post(
                OCR_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=120,
            )
        except requests.RequestException as e:
            return Response({'error': f'网络错误: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if resp.status_code != 200:
            return Response(
                {'error': f'OCR API 错误 {resp.status_code}: {resp.text[:300]}'},
                status=status.HTTP_502_BAD_GATEWAY,
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


# ─────────────────────────────────────────────────────────────
# Worker 中继模式（Redis Pub/Sub）
# ─────────────────────────────────────────────────────────────

class OCRProjectListView(APIView):
    """获取用户所有项目列表"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = OCRProject.objects.filter(user=request.user)
        return Response([{
            'id': p.id,
            'name': p.name,
            'total_pages': p.total_pages,
            'status': p.status,
            'processing_mode': p.processing_mode,
            'redis_channel': p.redis_channel,
            'created_at': p.created_at.isoformat(),
        } for p in projects])


class OCRProjectCreateView(APIView):
    """创建新项目"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        name = request.data.get('name', '').strip()
        processing_mode = request.data.get('processing_mode', 'api')

        if not name:
            return Response({'error': '请提供项目名称'}, status=status.HTTP_400_BAD_REQUEST)

        project = OCRProject.objects.create(
            id=_generate_project_id(),
            user=request.user,
            name=name,
            total_pages=0,
            processing_mode=processing_mode,
        )
        return Response({
            'id': project.id,
            'name': project.name,
            'processing_mode': project.processing_mode,
        }, status=status.HTTP_201_CREATED)


class OCRProjectDetailView(APIView):
    """获取项目详情（包含所有页面）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id, user=request.user)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目未找到'}, status=status.HTTP_404_NOT_FOUND)

        pages = project.pages.all()
        return Response({
            'id': project.id,
            'name': project.name,
            'total_pages': project.total_pages,
            'status': project.status,
            'processing_mode': project.processing_mode,
            'redis_channel': project.redis_channel,
            'created_at': project.created_at.isoformat(),
            'pages': [{
                'id': p.id,
                'page_num': p.page_num,
                'ocr_status': p.ocr_status,
                'ocr_result': p.ocr_result,
                'image_url': p.image_file.url if p.image_file else None,
                'feedback_type': p.feedback_type,
                'feedback_text': p.feedback_text,
                'submitted_at': p.submitted_at.isoformat() if p.submitted_at else None,
                'completed_at': p.completed_at.isoformat() if p.completed_at else None,
            } for p in pages],
        })


class OCRPageDetailView(APIView):
    """获取单页详情（轮询用）"""
    permission_classes = [IsAuthenticated]

    def get(self, request, page_id):
        try:
            page = OCRPage.objects.get(id=page_id, project__user=request.user)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面未找到'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'id': page.id,
            'project_id': page.project.id,
            'page_num': page.page_num,
            'image_url': page.image_file.url if page.image_file else None,
            'ocr_status': page.ocr_status,
            'ocr_result': page.ocr_result,
            'error_msg': page.error_msg,
            'feedback_type': page.feedback_type,
            'submitted_at': page.submitted_at.isoformat() if page.submitted_at else None,
            'completed_at': page.completed_at.isoformat() if page.completed_at else None,
        })


class OCRUploadView(APIView):
    """
    上传图片：
    - 自动缩放（最大边 ≤ 512）并压缩（JPEG 50% 或二值化 P 模式 PNG）
    - API 模式：直接返回 page_id，前端自己 POST /recognize/ 处理
    - Worker 模式：发布任务到 Redis，前端轮询 /pages/<id>/ 等待结果
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image = request.FILES.get('image')
        processing_mode = request.data.get('processing_mode', 'worker')
        project_id = request.data.get('project_id', '').strip()
        is_binary = request.data.get('is_binary', '0') == '1'

        if not image:
            return Response({'error': '请提供图片文件'}, status=status.HTTP_400_BAD_REQUEST)

        # 检查配额
        try:
            quota = _get_or_update_quota(request.user)
            if quota.left_count <= 0:
                return Response({'error': '今日识别次数已用完，点赞/点踩/提交修改可增加次数'},
                                status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception:
            pass

        # 图片预处理：缩放 + 压缩
        try:
            processed_file, _ = _process_image(image, is_binary=is_binary)
        except Exception:
            # 处理失败时使用原图
            image.seek(0)
            processed_file = image

        # 创建或获取项目
        if project_id:
            try:
                project = OCRProject.objects.get(id=project_id, user=request.user)
            except OCRProject.DoesNotExist:
                return Response({'error': '项目未找到'}, status=status.HTTP_404_NOT_FOUND)
        else:
            project = OCRProject.objects.create(
                id=_generate_project_id(),
                user=request.user,
                name=image.name,
                total_pages=1,
                processing_mode=processing_mode,
            )

        model_type = request.data.get('model_type', 'xuan')
        if model_type not in ('qing', 'xuan'):
            model_type = 'xuan'

        page_num = project.pages.count() + 1
        page = OCRPage.objects.create(
            project=project,
            page_num=page_num,
            image_path='',
            image_file=processed_file,
            ocr_status='pending',
            model_type=model_type,
            submitted_at=timezone.now(),
        )

        project.total_pages = project.pages.count()
        project.save()

        # 更新配额
        try:
            _get_or_update_quota(request.user, delta_upload=1, delta_nonfeedback=1)
        except Exception:
            pass

        # Worker 模式：发布任务到 Redis
        if processing_mode == 'worker':
            callback_token = _generate_callback_token()
            page.callback_token = callback_token
            page.save()

            site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
            task_payload = {
                "task_id":    page.id,
                "image_url":  f"{site_url}{page.image_file.url}",
                "callback_url": f"{site_url}/api/ocr/worker/callback/{callback_token}/",
                "project_id": project.id,
                "page_num":   page_num,
                "model_type": model_type,
            }

            channel = f"ocr_tasks_{model_type}"
            try:
                r = _get_redis()
                r.publish(channel, json.dumps(task_payload))
            except Exception:
                pass

        image_url = page.image_file.url if page.image_file else None
        return Response({
            'project_id': project.id,
            'page_id':    page.id,
            'model_type': model_type,
            'image_url':  image_url,
            'status':     'queued',
            'message':    f'MixTeX（{"青·小模型" if model_type=="qing" else "玄·大模型"}）：等待 OCR 处理器',
        }, status=status.HTTP_201_CREATED)


class OCRWorkerCallbackView(APIView):
    """Worker 处理完 OCR 后回调平台提交结果"""
    permission_classes = [AllowAny]

    def post(self, request, token):
        auth_error = _check_worker_token(request)
        if auth_error:
            return auth_error
        try:
            page = OCRPage.objects.get(callback_token=token)
        except OCRPage.DoesNotExist:
            return Response({'error': '无效的回调 Token'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text', '')
        error = request.data.get('error', '')

        if error:
            page.ocr_status = 'error'
            page.error_msg = error
        else:
            page.ocr_status = 'done'
            page.ocr_result = text

        page.completed_at = timezone.now()
        page.save()

        project = page.project
        all_pages = project.pages.all()
        done_count = all_pages.filter(ocr_status='done').count()
        if done_count == project.total_pages:
            project.status = 'done'
        else:
            project.status = 'processing'
        project.save()

        return Response({'success': True})


class OCRFeedbackView(APIView):
    """提交反馈（like / dislike / edit）"""
    permission_classes = [IsAuthenticated]

    def post(self, request, page_id):
        try:
            page = OCRPage.objects.get(id=page_id, project__user=request.user)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面未找到'}, status=status.HTTP_404_NOT_FOUND)

        feedback_type = request.data.get('type')   # 'like' / 'dislike' / 'edit'
        feedback_text = request.data.get('text', '')

        old_feedback = page.feedback_type
        if feedback_type in ['like', 'dislike', 'edit']:
            page.feedback_type = feedback_type
        if feedback_text:
            page.feedback_text = feedback_text
        page.save()

        # 仅第一次反馈计入配额增益
        if not old_feedback:
            try:
                if feedback_type == 'like':
                    # 点赞 +0.5次
                    _get_or_update_quota(request.user, delta_like=1, delta_nonfeedback=-1)
                elif feedback_type == 'dislike':
                    # 点踩 +0.5次
                    _get_or_update_quota(request.user, delta_dislike=1, delta_nonfeedback=-1)
                elif feedback_type == 'edit':
                    # 提交修改 +2次
                    _get_or_update_quota(request.user, delta_edit=1, delta_nonfeedback=-1)
            except Exception:
                pass

        return Response({'success': True})


class OCRQuotaView(APIView):
    """获取用户今日配额信息"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            quota = _get_or_update_quota(request.user)
        except Exception:
            return Response({'left_count': 50, 'upload_count': 0, 'like_count': 0,
                             'dislike_count': 0, 'edit_count': 0})

        return Response({
            'quota_date':        quota.quota_date.isoformat(),
            'upload_count':      quota.upload_count,
            'like_count':        quota.like_count,
            'dislike_count':     quota.dislike_count,
            'edit_count':        quota.edit_count,
            'nonfeedback_count': quota.nonfeedback_count,
            'used_count':        quota.used_count,
            'left_count':        quota.left_count,
        })


class OCRHistoryView(APIView):
    """获取用户历史识别记录（最近 100 条已完成页面）"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pages = (
            OCRPage.objects
            .filter(project__user=request.user, ocr_status='done')
            .select_related('project')
            .order_by('-completed_at')[:100]
        )
        result = []
        for p in pages:
            result.append({
                'id':           p.id,
                'project_id':   p.project.id,
                'project_name': p.project.name,
                'image_url':    p.image_file.url if p.image_file else None,
                'ocr_result':   p.ocr_result,
                'feedback_type': p.feedback_type,
                'feedback_text': p.feedback_text,
                'model_type':   p.model_type,
                'completed_at': p.completed_at.isoformat() if p.completed_at else None,
            })
        return Response(result)


# ─────────────────────────────────────────────────────────────
# 兼容旧 Worker 轮询（外部 Worker 拉取待处理图片）
# ─────────────────────────────────────────────────────────────

class OCREmptyTextView(APIView):
    """
    获取待处理页面列表（Worker HTTP 轮询模式）。
    支持 ?model_type=qing|xuan 过滤，Worker 按自身类型拉取对应任务。
    """
    permission_classes = [AllowAny]

    def get(self, request):
        auth_error = _check_worker_token(request)
        if auth_error:
            return auth_error
        qs = OCRPage.objects.filter(
            Q(ocr_result='') | Q(ocr_result__isnull=True),
            ocr_status='pending',
            image_file__isnull=False,
        )
        model_type = request.GET.get('model_type', '')
        if model_type in ('qing', 'xuan'):
            qs = qs.filter(model_type=model_type)

        pages_qs = qs.values('id', 'image_file', 'callback_token', 'model_type')[:10]

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:8000')
        result = []
        for p in pages_qs:
            image_url = f"{site_url}/media/{p['image_file']}" if p['image_file'] else None
            callback_url = (
                f"{site_url}/api/ocr/worker/callback/{p['callback_token']}/"
                if p['callback_token'] else ''
            )
            result.append({
                'id':           p['id'],
                'image_url':    image_url,
                'callback_url': callback_url,
                'model_type':   p['model_type'],
            })

        return Response({
            'empty_text_image_ids': [r['id'] for r in result],
            'pages': result,
        })


class OCRSubmitResultView(APIView):
    """兼容旧 Worker 的结果提交（POST image/{id}/ with text_data）"""
    permission_classes = [AllowAny]

    def post(self, request, page_id):
        auth_error = _check_worker_token(request)
        if auth_error:
            return auth_error
        try:
            page = OCRPage.objects.get(id=page_id)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面未找到'}, status=status.HTTP_404_NOT_FOUND)

        text = request.data.get('text_data') or request.data.get('text', '')
        if not text:
            return Response({'error': '请提供 text_data'}, status=status.HTTP_400_BAD_REQUEST)

        page.ocr_status = 'done'
        page.ocr_result = text
        page.completed_at = timezone.now()
        page.save()

        return Response({'status': 'success'})
