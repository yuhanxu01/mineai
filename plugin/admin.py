from django.contrib import admin
from .models import Plugin, PluginData


@admin.register(Plugin)
class PluginAdmin(admin.ModelAdmin):
    list_display = ('name', 'author', 'plugin_type', 'status', 'is_public', 'created_at')
    list_filter = ('status', 'plugin_type', 'is_public')
    search_fields = ('name', 'author__email', 'description')
    readonly_fields = ('slug', 'memory_offset', 'created_at', 'updated_at')
    actions = ['approve_plugins', 'reject_plugins']

    def approve_plugins(self, request, queryset):
        queryset.update(status=Plugin.STATUS_APPROVED)
        self.message_user(request, f'{queryset.count()} 个插件已上线。')
    approve_plugins.short_description = '批准选中插件'

    def reject_plugins(self, request, queryset):
        queryset.update(status=Plugin.STATUS_REJECTED)
        self.message_user(request, f'{queryset.count()} 个插件已拒绝。')
    reject_plugins.short_description = '拒绝选中插件'


@admin.register(PluginData)
class PluginDataAdmin(admin.ModelAdmin):
    list_display = ('plugin', 'user', 'key', 'updated_at')
    list_filter = ('plugin',)
    search_fields = ('plugin__name', 'user__email', 'key')
