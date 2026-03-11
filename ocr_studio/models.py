from django.db import models
from django.conf import settings


class OCRProject(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name="ocr_projects")
    """OCR 项目模型"""
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

    project = models.ForeignKey(
        OCRProject,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name='项目'
    )
    page_num = models.IntegerField(verbose_name='页码')
    image_path = models.CharField(max_length=1024, verbose_name='图片路径')
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

    class Meta:
        unique_together = [['project', 'page_num']]
        ordering = ['page_num']
        verbose_name = 'OCR页面'
        verbose_name_plural = 'OCR页面列表'

    def __str__(self):
        return f"Page {self.page_num} ({self.ocr_status})"
