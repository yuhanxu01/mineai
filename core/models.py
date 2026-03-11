from django.db import models


class APIConfig(models.Model):
    api_key = models.CharField(max_length=512)
    api_base = models.CharField(max_length=512, default='https://open.bigmodel.cn/api/paas/v4')
    chat_model = models.CharField(max_length=128, default='glm-4.7-flash')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    @classmethod
    def get_active(cls):
        return cls.objects.first()


class AgentLog(models.Model):
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('think', 'Think'),
        ('action', 'Action'),
        ('memory', 'Memory'),
        ('error', 'Error'),
        ('llm', 'LLM Call'),
    ]
    project_id = models.IntegerField(null=True, blank=True)
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default='info')
    title = models.CharField(max_length=256)
    content = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
