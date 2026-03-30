import re
from django.db import models
from django.conf import settings


class Plugin(models.Model):
    TYPE_CODE = 'code'
    TYPE_NOCODE = 'nocode'
    PLUGIN_TYPES = [
        (TYPE_CODE, 'Code Plugin'),
        (TYPE_NOCODE, 'No-Code Plugin'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUSES = [
        (STATUS_PENDING, '待审核'),
        (STATUS_APPROVED, '已上线'),
        (STATUS_REJECTED, '已拒绝'),
    ]

    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    icon = models.CharField(max_length=50, default='puzzle')
    color = models.CharField(max_length=20, default='#c9a86c')
    plugin_type = models.CharField(max_length=10, choices=PLUGIN_TYPES, default=TYPE_NOCODE)

    # Code Plugin: stores uploaded HTML content
    html_content = models.TextField(blank=True)

    # No-Code Plugin: JSON config {system_prompt, model, welcome_msg, input_placeholder}
    config = models.JSONField(default=dict)

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='plugins')
    status = models.CharField(max_length=10, choices=STATUSES, default=STATUS_PENDING)
    is_public = models.BooleanField(default=True)

    # Memory pyramid namespace: 700000 + id to avoid collisions with other apps
    memory_offset = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        author_name = getattr(self.author, 'email', None) or getattr(self.author, 'username', None) or str(self.author_id)
        return f'{self.name} ({author_name})'

    def save(self, *args, **kwargs):
        if not self.slug:
            base = re.sub(r'[^a-z0-9]+', '-', self.name.lower()).strip('-') or 'plugin'
            slug = base
            counter = 1
            while Plugin.objects.filter(slug=slug).exists():
                slug = f'{base}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
        # Set memory_offset after first save when id is available
        if not self.memory_offset:
            Plugin.objects.filter(pk=self.pk).update(memory_offset=700000 + self.pk)
            self.memory_offset = 700000 + self.pk


class PluginData(models.Model):
    """Per-user KV storage for each plugin."""
    plugin = models.ForeignKey(Plugin, on_delete=models.CASCADE, related_name='data')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='plugin_data')
    key = models.CharField(max_length=255)
    value = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['plugin', 'user', 'key']]

    def __str__(self):
        user_name = getattr(self.user, 'email', None) or getattr(self.user, 'username', None) or str(self.user_id)
        return f'{self.plugin.slug}:{user_name}:{self.key}'
