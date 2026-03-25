from django.db import models
from django.conf import settings

class Conversation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_conversations')
    title = models.CharField(max_length=255, default='New Chat')
    model_name = models.CharField(max_length=50, default='glm-4.7-flash')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Enforce 20 conversation limit per user by deleting the oldest ones
            user_convs = Conversation.objects.filter(user=self.user).order_by('-updated_at')
            if user_convs.count() > 20:
                convs_to_delete = user_convs[20:]
                for conv in convs_to_delete:
                    conv.delete()

class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=[('user', 'User'), ('assistant', 'Assistant'), ('system', 'System')])
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
