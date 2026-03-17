from django.db import models
from django.conf import settings


class Question(models.Model):
    STATUS_DRAFT = 'draft'
    STATUS_PUBLISHED = 'published'
    STATUS_CHOICES = [
        (STATUS_DRAFT, '草稿'),
        (STATUS_PUBLISHED, '已发布'),
    ]

    MODEL_TEXT = 'glm-4.7-flash'
    MODEL_VISION = 'glm-4v-flash'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='qbank_questions',
    )
    title = models.CharField(max_length=500, blank=True, default='')
    content = models.TextField(
        help_text='题目文字内容（OCR识别或手动输入）',
        blank=True,
        default='',
    )
    original_image = models.TextField(
        blank=True, default='',
        help_text='原始题目图片 base64（不含 data: 前缀）',
    )
    image_type = models.CharField(
        max_length=20, blank=True, default='',
        help_text='图片 MIME 类型后缀，如 jpeg / png',
    )
    model_used = models.CharField(
        max_length=50,
        default='glm-4.7-flash',
        help_text='当前使用的 AI 模型',
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT,
    )
    tags = models.CharField(max_length=200, blank=True, default='')
    subject = models.CharField(max_length=100, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title or f'题目 #{self.pk}'


class ChatMessage(models.Model):
    ROLE_USER = 'user'
    ROLE_ASSISTANT = 'assistant'
    ROLE_CHOICES = [
        (ROLE_USER, '用户'),
        (ROLE_ASSISTANT, 'AI'),
    ]

    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, related_name='messages',
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    model_used = models.CharField(max_length=50, default='glm-4.7-flash')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class FinalAnswer(models.Model):
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name='final_answer',
    )
    content = models.TextField(help_text='最终答案（Markdown 格式）')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'最终答案 for #{self.question_id}'


class StandardAnswer(models.Model):
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name='standard_answer',
    )
    content_md = models.TextField(blank=True, default='', help_text='标准答案 Markdown 文本')
    image = models.TextField(blank=True, default='', help_text='标准答案图片 base64')
    image_type = models.CharField(max_length=20, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class SharedQuestion(models.Model):
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, related_name='shared',
    )
    view_count = models.PositiveIntegerField(default=0)
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published_at']

    def like_count(self):
        return self.likes.count()

    def favorite_count(self):
        return self.favorites.count()

    def comment_count(self):
        return self.comments.count()


class Comment(models.Model):
    shared_question = models.ForeignKey(
        SharedQuestion, on_delete=models.CASCADE, related_name='comments',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class Like(models.Model):
    shared_question = models.ForeignKey(
        SharedQuestion, on_delete=models.CASCADE, related_name='likes',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shared_question', 'user')


class Favorite(models.Model):
    shared_question = models.ForeignKey(
        SharedQuestion, on_delete=models.CASCADE, related_name='favorites',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('shared_question', 'user')
