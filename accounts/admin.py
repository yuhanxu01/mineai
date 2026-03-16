from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from accounts.models import User, TokenUsage, SiteConfig, VerificationCode


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff')
    search_fields = ('email',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2')}),
    )
    filter_horizontal = ()


@admin.register(TokenUsage)
class TokenUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt_count', 'input_tokens', 'output_tokens', 'total_tokens', 'updated_at')
    readonly_fields = ('user', 'prompt_count', 'input_tokens', 'output_tokens', 'total_tokens', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """单例配置页：禁止新增和删除，直接编辑唯一的一行。"""
    fieldsets = (
        ('验证码发送限制', {
            'description': '调整以下参数控制注册验证码的发送策略。修改后立即生效，无需重启服务。',
            'fields': (
                'code_cooldown_seconds',
                'code_expire_minutes',
                'code_daily_limit',
                'code_minute_limit',
            ),
        }),
        ('免费用户每日Token配额', {
            'description': '未配置自己API密钥的用户每自然日可使用的资源上限。管理员和已配置API密钥的用户不受此限制。',
            'fields': (
                'free_daily_input_tokens',
                'free_daily_output_tokens',
                'free_daily_prompt_count',
            ),
        }),
        ('只读信息', {
            'fields': ('updated_at',),
        }),
    )
    readonly_fields = ('updated_at',)

    def has_add_permission(self, request):
        return not SiteConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        """列表页直接跳转到单例的编辑页。"""
        obj, _ = SiteConfig.objects.get_or_create(pk=1)
        from django.shortcuts import redirect
        return redirect(f'/admin/accounts/siteconfig/{obj.pk}/change/')


@admin.register(VerificationCode)
class VerificationCodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'code_masked', 'is_used', 'created_at', 'status_badge')
    list_filter = ('is_used',)
    search_fields = ('email',)
    ordering = ('-created_at',)
    readonly_fields = ('email', 'code', 'is_used', 'created_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def code_masked(self, obj):
        return f'{obj.code[:2]}****'
    code_masked.short_description = '验证码'

    def status_badge(self, obj):
        from django.utils import timezone
        from datetime import timedelta
        cfg = SiteConfig.get()
        expired = (timezone.now() - obj.created_at).total_seconds() > cfg.code_expire_minutes * 60
        if obj.is_used:
            return format_html('<span style="color:#5eb87a">已使用</span>')
        if expired:
            return format_html('<span style="color:#686460">⌛ 已过期</span>')
        return format_html('<span style="color:#c9a86c">● 有效</span>')
    status_badge.short_description = '状态'
