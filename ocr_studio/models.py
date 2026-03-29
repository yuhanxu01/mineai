import uuid
from django.db import models
from django.conf import settings


class OCRProject(models.Model):
    """OCR 项目模型"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="ocr_projects")
    id = models.CharField(max_length=12, primary_key=True, verbose_name='项目ID')
    name = models.CharField(max_length=512, verbose_name='文件名')
    total_pages = models.IntegerField(verbose_name='总页数')
    api_key = models.CharField(max_length=512, blank=True, verbose_name='API密钥')
    ocr_prompt = models.TextField(blank=True, verbose_name='OCR提示词')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    status = models.CharField(
        max_length=20,
        default='uploaded',
        verbose_name='状态'
    )

    # 新增：处理模式
    PROCESSING_MODE_CHOICES = [
        ('api', '直连API模式'),       # 浏览器直接调用后端 OCR API
        ('worker', 'Worker中继模式'), # 图片存储，通过 Redis 推送给 Worker
    ]
    processing_mode = models.CharField(
        max_length=20,
        choices=PROCESSING_MODE_CHOICES,
        default='api',
        verbose_name='处理模式'
    )

    # 新增：Redis 频道名称（可选，默认使用 'ocr_tasks'）
    redis_channel = models.CharField(
        max_length=100,
        default='ocr_tasks',
        help_text="Redis Pub/Sub 频道名称，Worker 订阅此频道接收任务"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'OCR项目'
        verbose_name_plural = 'OCR项目列表'

    def __str__(self):
        return f"{self.name} ({self.total_pages}页)"


class OCRPage(models.Model):
    """OCR 页面模型"""
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('processing', '处理中'),
        ('done', '已完成'),
        ('error', '错误'),
    ]
    MODEL_TYPE_CHOICES = [
        ('qing', '青·小模型'),
        ('xuan', '玄·大模型'),
    ]

    FEEDBACK_CHOICES = [
        ('like', '点赞'),
        ('dislike', '点踩'),
    ]

    project = models.ForeignKey(
        OCRProject,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name='项目'
    )
    page_num = models.IntegerField(verbose_name='页码')
    image_path = models.CharField(max_length=1024, blank=True, verbose_name='图片路径')

    # 新增：实际存储图片文件（用于 Worker 中继模式）
    image_file = models.ImageField(
        upload_to='ocr_pages/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='图片文件'
    )

    # 新增：OpenCV.js 预处理结果（可选，存储二值化后的图片）
    binary_image = models.ImageField(
        upload_to='ocr_pages_binary/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='二值化图片'
    )
    model_type = models.CharField(
        max_length=20,
        choices=MODEL_TYPE_CHOICES,
        default='xuan',
        verbose_name='OCR 模型',
    )

    ocr_status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='OCR状态'
    )
    ocr_result = models.TextField(blank=True, verbose_name='OCR结果')
    error_msg = models.TextField(blank=True, verbose_name='错误信息')
    submitted_at = models.DateTimeField(null=True, blank=True, verbose_name='提交时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')

    # 新增：反馈系统（复刻旧项目的 feedback 字段）
    feedback_type = models.CharField(
        max_length=20,
        choices=FEEDBACK_CHOICES,
        null=True,
        blank=True,
        verbose_name='反馈类型'
    )
    feedback_text = models.TextField(blank=True, verbose_name='反馈文本')

    # 新增：Worker 回调认证（防止伪造提交）
    callback_token = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        verbose_name='回调令牌'
    )

    class Meta:
        unique_together = [['project', 'page_num']]
        ordering = ['page_num']
        verbose_name = 'OCR页面'
        verbose_name_plural = 'OCR页面列表'

    def __str__(self):
        return f"Page {self.page_num} ({self.ocr_status})"


class OCRUsageQuota(models.Model):
    """24小时 OCR 配额追踪（类似旧项目的 24 小时限制）"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ocr_quota')
    quota_date = models.DateField(verbose_name='配额日期')
    upload_count = models.IntegerField(default=0, verbose_name='上传次数')
    like_count = models.IntegerField(default=0, verbose_name='点赞次数')
    dislike_count = models.IntegerField(default=0, verbose_name='点踩次数')
    nonfeedback_count = models.IntegerField(default=0, verbose_name='未反馈次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'OCR配额'
        verbose_name_plural = 'OCR配额列表'
        unique_together = [['user', 'quota_date']]

    def __str__(self):
        return f"{self.user.username} - {self.quota_date}"

    @property
    def used_count(self):
        # 复刻旧项目公式：2*nonfeedback - upload + 1.5*like
        return 2 * self.nonfeedback_count - self.upload_count + 1.5 * self.like_count

    @property
    def left_count(self):
        # 默认每日 10 次上限
        return max(0, 10 - self.used_count)
