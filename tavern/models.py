from django.db import models
from django.conf import settings


class TavernDeployment(models.Model):
    """
    单例：记录 SillyTavern 部署配置。
    管理员在后台配置，普通用户只读。
    """
    base_url = models.CharField(
        max_length=300,
        default='http://localhost:8001',
        help_text='SillyTavern 服务地址（如 http://localhost:8001 或 https://tavern.example.com）',
    )
    data_dir = models.CharField(
        max_length=500,
        blank=True,
        help_text='SillyTavern 的 data 目录绝对路径（用于自动创建用户，如 /opt/SillyTavern/data）',
    )
    admin_handle = models.CharField(
        max_length=50,
        default='admin',
        help_text='SillyTavern 管理员账号 handle',
    )
    allow_frame_embed = models.BooleanField(
        default=True,
        help_text='是否允许在 MineAI 内嵌 iframe（需要 SillyTavern 允许同域或已禁用 X-Frame-Options）',
    )
    setup_note = models.TextField(
        blank=True,
        help_text='给用户看的说明文字（支持 Markdown）',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'SillyTavern 部署配置'

    def __str__(self):
        return f'SillyTavern @ {self.base_url}'


class TavernAccount(models.Model):
    """
    记录每个 MineAI 用户对应的 SillyTavern 账号。
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tavern_account',
    )
    handle = models.CharField(max_length=50, unique=True, help_text='SillyTavern 用户 handle')
    password = models.CharField(max_length=200, help_text='明文密码（用于展示给用户）')
    provisioned_at = models.DateTimeField(auto_now_add=True)
    last_accessed = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'SillyTavern 账号'
        ordering = ['-provisioned_at']

    def __str__(self):
        return f'{self.user.username} → {self.handle}'
