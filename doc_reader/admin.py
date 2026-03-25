from django.contrib import admin
from .models import (
    DocumentProject, DocumentPage, ParseSession,
    ChatSession, ChatMessage
)


@admin.register(DocumentProject)
class DocumentProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'file_type', 'total_pages', 'cached_pages_count', 'cache_size_bytes', 'created_at']
    list_filter = ['file_type', 'created_at']
    search_fields = ['name', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(DocumentPage)
class DocumentPageAdmin(admin.ModelAdmin):
    list_display = ['document', 'page_num', 'ocr_status', 'page_image_size', 'cached_at']
    list_filter = ['ocr_status', 'cached_at']
    search_fields = ['document__name']
    readonly_fields = ['cached_at']


@admin.register(ParseSession)
class ParseSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'user', 'status', 'total_pages', 'completed_pages', 'failed_pages', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['document__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'user', 'title', 'created_at', 'updated_at']
    list_filter = ['created_at']
    search_fields = ['title', 'document__name', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'instruction_type', 'model', 'created_at']
    list_filter = ['role', 'instruction_type', 'created_at']
    search_fields = ['content', 'session__title']
    readonly_fields = ['created_at']
