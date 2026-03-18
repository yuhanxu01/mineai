"""
scan_enhance/views.py
后端 API：状态端点 + 云端图片上传（5层安全）
"""
import io
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status

from .models import UserUpload, ALLOWED_MIME_TYPES, MAX_UPLOAD_SIZE


class StatusView(APIView):
    """返回处理模式：client-side JS，无需 OpenCV。"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'mode': 'client',
            'js_processing': True,
            'cv2_available': False,
            'message': '所有图像处理运行在浏览器端 Web Worker 中，无需服务器 CPU。',
        })


def _serialize_upload(upload, request):
    return {
        'id': upload.id,
        'original_name': upload.original_name,
        'url': request.build_absolute_uri(upload.file.url),
        'file_size': upload.file_size,
        'mime_type': upload.mime_type,
        'created_at': upload.created_at.isoformat(),
    }


class UserUploadListCreateView(APIView):
    """GET: 列出当前用户的上传记录  POST: 上传新图片"""
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    # ── GET: 返回该用户最近 50 条记录 ─────────────────────────
    def get(self, request):
        uploads = UserUpload.objects.filter(user=request.user)[:50]
        return Response([_serialize_upload(u, request) for u in uploads])

    # ── POST: 上传并 5 层验证 ─────────────────────────────────
    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': '缺少 file 字段'}, status=status.HTTP_400_BAD_REQUEST)

        # 层 2：大小限制（服务端硬校验，不依赖前端）
        if file.size > MAX_UPLOAD_SIZE:
            size_mb = file.size / (1024 * 1024)
            return Response(
                {'error': f'文件超过 50MB 限制（当前 {size_mb:.1f} MB）'},
                status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            )

        # 层 3：MIME 白名单
        content_type = file.content_type or ''
        if content_type not in ALLOWED_MIME_TYPES:
            return Response(
                {'error': f'不支持的文件类型：{content_type}（仅允许图片格式）'},
                status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            )

        # 层 4：Pillow magic bytes —— 实际解码验证文件是真实图片
        try:
            from PIL import Image
            file.seek(0)
            raw = file.read(4096)  # 读头部足够验证
            try:
                img = Image.open(io.BytesIO(raw + file.read()))
                img.verify()  # 验证文件完整性
            except Exception:
                # 部分格式 verify 后不可再读，再试一次完整内容
                file.seek(0)
                try:
                    img2 = Image.open(file)
                    img2.verify()
                except Exception as e:
                    return Response(
                        {'error': f'文件内容不是有效图片：{e}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            file.seek(0)
        except ImportError:
            # Pillow 未安装时，跳过此层（记录警告）
            file.seek(0)

        # 层 5：用户配额（每用户 ≤200 条）
        count = UserUpload.objects.filter(user=request.user).count()
        if count >= 200:
            return Response(
                {'error': '已达到上传上限（200 张），请先删除一些旧记录'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 全部通过 → 保存
        original_name = file.name[:512]  # 截断防超长
        upload = UserUpload(
            user=request.user,
            original_name=original_name,
            file_size=file.size,
            mime_type=content_type,
        )
        upload.file.save('', file, save=False)  # file.name 交给 upload_to_path
        upload.save()

        return Response(_serialize_upload(upload, request), status=status.HTTP_201_CREATED)


class UserUploadDetailView(APIView):
    """DELETE /api/scan/uploads/<pk>/ — 只能删自己的"""
    permission_classes = [IsAuthenticated]

    def _get_own_or_404(self, request, pk):
        try:
            return UserUpload.objects.get(pk=pk, user=request.user)
        except UserUpload.DoesNotExist:
            raise Http404

    def get(self, request, pk):
        upload = self._get_own_or_404(request, pk)
        return Response(_serialize_upload(upload, request))

    def delete(self, request, pk):
        upload = self._get_own_or_404(request, pk)
        # 同步删除实际文件
        try:
            upload.file.delete(save=False)
        except Exception:
            pass
        upload.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
