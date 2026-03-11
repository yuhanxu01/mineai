from django.conf import settings
from django.db import models


class Project(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField(max_length=512)
    genre = models.CharField(max_length=128, blank=True, default='')
    synopsis = models.TextField(blank=True, default='')
    style_guide = models.TextField(blank=True, default='')
    world_setting = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title


class Chapter(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chapters')
    number = models.IntegerField()
    title = models.CharField(max_length=512)
    outline = models.TextField(blank=True, default='')
    content = models.TextField(blank=True, default='')
    word_count = models.IntegerField(default=0)
    memory_node_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, default='draft', choices=[
        ('outline', 'Outline'),
        ('draft', 'Draft'),
        ('writing', 'Writing'),
        ('review', 'Review'),
        ('done', 'Done'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['number']
        unique_together = ('project', 'number')

    def __str__(self):
        return f"Ch.{self.number}: {self.title}"

    def save(self, *args, **kwargs):
        self.word_count = len(self.content.split()) if self.content else 0
        super().save(*args, **kwargs)
