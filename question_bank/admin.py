from django.contrib import admin
from .models import Question, ChatMessage, FinalAnswer, StandardAnswer, SharedQuestion, Comment, Like, Favorite


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'subject', 'model_used', 'status', 'created_at')
    list_filter = ('status', 'model_used', 'subject')
    search_fields = ('title', 'content', 'user__email')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'role', 'model_used', 'created_at')
    list_filter = ('role', 'model_used')


@admin.register(FinalAnswer)
class FinalAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'updated_at')


@admin.register(StandardAnswer)
class StandardAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'updated_at')


@admin.register(SharedQuestion)
class SharedQuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question', 'view_count', 'published_at')


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'shared_question', 'user', 'created_at')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'shared_question', 'user', 'created_at')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'shared_question', 'user', 'created_at')
