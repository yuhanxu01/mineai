from django.db import models
from django.conf import settings


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
    # Store the last-applied operation params as JSON
    last_ops = models.JSONField(default=dict, blank=True, verbose_name='最近处理参数')

    class Meta:
        unique_together = [['project', 'page_num']]
        ordering = ['page_num']
        verbose_name = '扫描页面'
        verbose_name_plural = '扫描页面列表'

    def __str__(self):
        return f"{self.project.name} - Page {self.page_num}"
