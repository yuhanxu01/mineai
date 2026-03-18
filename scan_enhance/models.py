from django.db import models
from django.conf import settings
import uuid
import os


def upload_to_path(instance, filename):
    """Generate a UUID-based storage path to prevent filename attacks."""
    ext = os.path.splitext(filename)[1].lower()
    safe_ext = ext if ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif') else '.bin'
    return f"uploads/{instance.user_id}/{uuid.uuid4().hex}{safe_ext}"


# ── 扫描增强旧有模型 ──────────────────────────────────────────
class ScanProject(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='scan_projects'
    )
    name = models.CharField(max_length=512, verbose_name='文件名')
    total_pages = models.IntegerField(default=1, verbose_name='总页数')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '扫描项目'
        verbose_name_plural = '扫描项目列表'

    def __str__(self):
        return self.name


class ScanPage(models.Model):
    project = models.ForeignKey(
        ScanProject,
        on_delete=models.CASCADE,
        related_name='pages'
    )
    page_num = models.IntegerField(verbose_name='页码')
    original_path = models.CharField(max_length=1024, verbose_name='原始图片路径')
    processed_path = models.CharField(max_length=1024, blank=True, verbose_name='处理后图片路径')
    last_ops = models.JSONField(default=dict, blank=True, verbose_name='最近处理参数')

    class Meta:
        unique_together = [['project', 'page_num']]
        ordering = ['page_num']
        verbose_name = '扫描页面'
        verbose_name_plural = '扫描页面列表'

    def __str__(self):
        return f"{self.project.name} - Page {self.page_num}"


# ── 云端图片上传 ──────────────────────────────────────────────
ALLOWED_MIME_TYPES = frozenset({
    'image/jpeg', 'image/png', 'image/webp',
    'image/gif', 'image/bmp', 'image/tiff',
})
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


class UserUpload(models.Model):
    """用户主动上传至云端的图片文件（每用户最多 200 条）。"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='scan_uploads',
    )
    original_name = models.CharField(max_length=512, verbose_name='原始文件名')
    file = models.FileField(upload_to=upload_to_path, max_length=1024, verbose_name='文件')
    file_size = models.PositiveIntegerField(verbose_name='文件大小(bytes)')
    mime_type = models.CharField(max_length=64, verbose_name='MIME 类型')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '用户上传'
        verbose_name_plural = '用户上传列表'

    def __str__(self):
        return f"{self.user} — {self.original_name}"
