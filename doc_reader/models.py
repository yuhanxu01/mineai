from django.db import models
from django.conf import settings
import os


USER_CACHE_QUOTA_BYTES = 200 * 1024 * 1024  # 200 MB per user


def page_upload_path(instance, filename):
    """Upload to media/doc_reader_pages/<user_id>/<document_id>/<page_num>.png"""
    return f'doc_reader_pages/{instance.document.user_id}/{instance.document_id}/{instance.page_num}.png'


class DocumentProject(models.Model):
    """文档阅读项目"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doc_projects')
    id = models.CharField(max_length=12, primary_key=True)

    # 关联的云盘文件（可选，用户也可选择不上传直接读取本地文件）
    cloud_file = models.ForeignKey(
        'accounts.CloudFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='doc_projects',
        verbose_name='云盘文件'
    )

    name = models.CharField(max_length=512, verbose_name='文档名称')
    file_type = models.CharField(max_length=10, choices=[
        ('pdf', 'PDF'),
        ('md', 'Markdown'),
        ('txt', 'Text'),
    ], default='pdf', verbose_name='文件类型')

    total_pages = models.IntegerField(default=0, verbose_name='总页数')
    file_size = models.PositiveBigIntegerField(default=0, verbose_name='文件大小(字节)')

    # 缓存统计
    cached_pages_count = models.IntegerField(default=0, verbose_name='已缓存页数')
    cache_size_bytes = models.PositiveBigIntegerField(default=0, verbose_name='缓存大小(字节)')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '文档项目'
        verbose_name_plural = '文档项目列表'

    def __str__(self):
        return f"{self.name} ({self.get_file_type_display()})"

    def update_cache_stats(self):
        """更新缓存统计"""
        from django.db.models import Sum
        pages = self.pages.aggregate(
            count=models.Count('id'),
            total_size=models.Sum('page_image_size')
        )
        self.cached_pages_count = pages['count'] or 0
        self.cache_size_bytes = pages['total_size'] or 0
        self.save(update_fields=['cached_pages_count', 'cache_size_bytes'])


class DocumentPage(models.Model):
    """PDF页面缓存（用于GLM-OCR解析）"""
    document = models.ForeignKey(
        DocumentProject,
        on_delete=models.CASCADE,
        related_name='pages',
        verbose_name='文档'
    )
    page_num = models.IntegerField(verbose_name='页码（从1开始）')

    # 渲染后的页面图片（PNG，用于OCR）
    page_image = models.ImageField(
        upload_to=page_upload_path,
        null=True,
        blank=True,
        verbose_name='页面图片'
    )
    page_image_size = models.PositiveBigIntegerField(default=0, verbose_name='图片大小(字节)')

    # 页面尺寸信息
    page_width = models.IntegerField(null=True, blank=True, verbose_name='原始宽度')
    page_height = models.IntegerField(null=True, blank=True, verbose_name='原始高度')

    # OCR解析状态
    ocr_status = models.CharField(max_length=20, choices=[
        ('pending', '待解析'),
        ('processing', '解析中'),
        ('done', '已完成'),
        ('error', '错误'),
    ], default='pending', verbose_name='解析状态')

    ocr_result_raw = models.TextField(blank=True, verbose_name='OCR原始结果(JSON)')
    ocr_result_md = models.TextField(blank=True, verbose_name='OCR Markdown结果')

    # 布局解析详细结果（layout_details数组）
    layout_details = models.JSONField(default=list, blank=True, verbose_name='布局详情')

    error_msg = models.TextField(blank=True, verbose_name='错误信息')

    cached_at = models.DateTimeField(auto_now_add=True, verbose_name='缓存时间')

    class Meta:
        unique_together = [['document', 'page_num']]
        ordering = ['page_num']
        verbose_name = '文档页面'
        verbose_name_plural = '文档页面列表'

    def __str__(self):
        return f"{self.document.name} - 第{self.page_num}页"


class ParseSession(models.Model):
    """解析会话（跟踪一次批量解析任务）"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parse_sessions')
    document = models.ForeignKey(DocumentProject, on_delete=models.CASCADE, related_name='parse_sessions')

    status = models.CharField(max_length=20, choices=[
        ('pending', '待处理'),
        ('running', '进行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ], default='pending', verbose_name='状态')

    total_pages = models.IntegerField(default=0, verbose_name='总页数')
    completed_pages = models.IntegerField(default=0, verbose_name='已完成页数')
    failed_pages = models.IntegerField(default=0, verbose_name='失败页数')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '解析会话'
        verbose_name_plural = '解析会话列表'

    def __str__(self):
        return f"{self.document.name} - {self.get_status_display()}"


class ChatSession(models.Model):
    """与文档的对话会话"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='doc_chat_sessions')
    document = models.ForeignKey(DocumentProject, on_delete=models.CASCADE, related_name='chat_sessions')

    title = models.CharField(max_length=255, default='新对话', verbose_name='对话标题')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话列表'

    def __str__(self):
        return f"{self.document.name} - {self.title}"


class ChatMessage(models.Model):
    """对话消息"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=10, choices=[
        ('user', '用户'),
        ('assistant', '助手'),
    ], verbose_name='角色')

    # 用户选择的文本片段（来自OCR结果）
    selected_texts = models.JSONField(default=list, blank=True, verbose_name='选中的文本片段')

    content = models.TextField(verbose_name='消息内容')

    # 使用的指令类型（translate, summarize, explain, custom）
    instruction_type = models.CharField(max_length=20, blank=True, verbose_name='指令类型')

    # 使用的模型
    model = models.CharField(max_length=50, blank=True, verbose_name='使用的模型')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        ordering = ['created_at']
        verbose_name = '对话消息'
        verbose_name_plural = '对话消息列表'

    def __str__(self):
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.get_role_display()}: {content_preview}"
