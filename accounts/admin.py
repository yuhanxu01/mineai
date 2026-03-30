from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from django import forms
from accounts.models import User, TokenUsage, SiteConfig, VerificationCode, CloudFile, DonationRecord


class AddPointsForm(forms.Form):
    delta = forms.FloatField(label='增减积分', help_text='正数=增加，负数=扣减')


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'points_display', 'is_active', 'is_staff', 'created_at')
    list_filter = ('is_active', 'is_staff', 'is_guest')
    search_fields = ('email',)
    ordering = ('-created_at',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('权限', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('积分', {'fields': ('points',), 'description': '1积分=2万输出Token / 1积分=5万输入Token'}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'password1', 'password2')}),
    )
    filter_horizontal = ()

    def points_display(self, obj):
        color = '#c9a86c' if obj.points > 0 else '#888'
        return format_html('<span style="color:{};font-weight:600">{:.2f}</span>', color, obj.points)
    points_display.short_description = '积分'
    points_display.admin_order_field = 'points'


@admin.register(TokenUsage)
class TokenUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'prompt_count', 'input_tokens', 'output_tokens', 'total_tokens', 'updated_at')
    readonly_fields = ('user', 'prompt_count', 'input_tokens', 'output_tokens', 'total_tokens', 'updated_at')
    search_fields = ('user__email',)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    """单例配置页：禁止新增和删除，直接编辑唯一的一行。"""
    fieldsets = (
        ('网站品牌', {
            'description': '自定义浏览器标签页标题、图标，以及页面上的网站名称和副标题。修改后立即生效。',
            'fields': (
                'site_title',
                'site_subtitle',
                'site_favicon',
            ),
        }),
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


@admin.register(DonationRecord)
class DonationRecordAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'amount_points', 'note', 'status_badge', 'created_at', 'approve_action')
    list_filter = ('status',)
    search_fields = ('user__email', 'note')
    ordering = ('-created_at',)
    readonly_fields = ('user', 'amount_points', 'note', 'created_at', 'reviewed_at')
    actions = ['approve_selected', 'reject_selected']

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = '用户邮箱'

    def status_badge(self, obj):
        color = {'pending': '#c9a86c', 'approved': '#5eb87a', 'rejected': '#c45a5a'}.get(obj.status, '#888')
        return format_html('<span style="color:{};font-weight:600">{}</span>', color, obj.get_status_display())
    status_badge.short_description = '状态'

    def approve_action(self, obj):
        if obj.status == 'pending':
            return format_html(
                '<a href="/admin/accounts/donationrecord/{}/change/" style="color:#c9a86c">审核</a>', obj.pk
            )
        return '—'
    approve_action.short_description = '操作'

    @admin.action(description='批准选中的赞赏申请')
    def approve_selected(self, request, queryset):
        from django.utils import timezone
        count = 0
        for record in queryset.filter(status='pending').select_related('user'):
            record.status = 'approved'
            record.reviewed_at = timezone.now()
            record.save(update_fields=['status', 'reviewed_at'])
            record.user.points = record.user.points + record.amount_points
            record.user.save(update_fields=['points'])
            count += 1
        self.message_user(request, f'已批准 {count} 条赞赏，积分已发放')

    @admin.action(description='拒绝选中的赞赏申请')
    def reject_selected(self, request, queryset):
        from django.utils import timezone
        count = queryset.filter(status='pending').update(status='rejected', reviewed_at=timezone.now())
        self.message_user(request, f'已拒绝 {count} 条赞赏申请')


@admin.register(CloudFile)
class CloudFileAdmin(admin.ModelAdmin):
    list_display = ('user', 'name', 'file_type', 'size_display', 'uploaded_at')
    list_filter = ('file_type',)
    search_fields = ('user__email', 'name')
    ordering = ('-uploaded_at',)
    readonly_fields = ('user', 'name', 'size', 'file_type', 'file', 'sha256', 'uploaded_at')

    def has_add_permission(self, request):
        return False

    def size_display(self, obj):
        kb = obj.size / 1024
        if kb < 1024:
            return f'{kb:.1f} KB'
        return f'{kb/1024:.2f} MB'
    size_display.short_description = '大小'
