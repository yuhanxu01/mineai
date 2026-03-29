import hashlib
import os
import secrets
import uuid
from datetime import timedelta, date

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password):
        if not email:
            raise ValueError('邮箱不能为空')
        user = self.model(email=self.normalize_email(email))
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


CLOUD_QUOTA_BYTES = 50 * 1024 * 1024  # 50 MB


def cloud_upload_path(instance, filename):
    """Upload to media/cloud/<user_id>/<filename>"""
    filename = os.path.basename(filename)
    return f'cloud/{instance.user_id}/{filename}'


ALLOWED_EXTENSIONS = {
    '.pdf', '.txt', '.md',
    '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg',
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp',
    '.cc', '.h', '.hpp', '.go', '.rs', '.sh', '.bash', '.zsh',
    '.html', '.css', '.scss', '.json', '.yaml', '.yml', '.toml',
    '.xml', '.csv', '.sql', '.r', '.rb', '.php', '.swift', '.kt',
}

ALLOWED_MIME_PREFIXES = (
    'text/',
    'image/',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats',
    'application/vnd.ms-',
    'application/json',
    'application/xml',
)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='邮箱')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_guest = models.BooleanField(default=False, verbose_name='是否访客')
    created_at = models.DateTimeField(auto_now_add=True)
    user_api_key = models.CharField(max_length=512, blank=True, default='', verbose_name='用户自定义API密钥')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = '用户'
        verbose_name_plural = '用户'

    def __str__(self):
        return self.email

    @property
    def cloud_used_bytes(self):
        from django.db.models import Sum
        agg = self.cloud_files.aggregate(total=Sum('size'))
        return agg['total'] or 0

    @property
    def cloud_quota_bytes(self):
        return CLOUD_QUOTA_BYTES


class TokenUsage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token_usage')
    prompt_count = models.PositiveIntegerField(default=0, verbose_name='提交次数')
    input_tokens = models.BigIntegerField(default=0, verbose_name='输入Token')
    output_tokens = models.BigIntegerField(default=0, verbose_name='输出Token')
    total_tokens = models.BigIntegerField(default=0, verbose_name='总Token')
    # 每日用量（自动按自然日重置）
    daily_date = models.DateField(null=True, blank=True, verbose_name='当日日期')
    daily_prompt_count = models.PositiveIntegerField(default=0, verbose_name='今日提交次数')
    daily_input_tokens = models.BigIntegerField(default=0, verbose_name='今日输入Token')
    daily_output_tokens = models.BigIntegerField(default=0, verbose_name='今日输出Token')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Token用量'

    @classmethod
    def record(cls, user_id, usage_data):
        today = date.today()
        obj, _ = cls.objects.get_or_create(user_id=user_id)
        # 如果日期变了，先重置当日计数
        if obj.daily_date != today:
            cls.objects.filter(user_id=user_id).update(
                daily_date=today,
                daily_prompt_count=0,
                daily_input_tokens=0,
                daily_output_tokens=0,
            )
        cls.objects.filter(user_id=user_id).update(
            prompt_count=models.F('prompt_count') + 1,
            input_tokens=models.F('input_tokens') + usage_data.get('prompt_tokens', 0),
            output_tokens=models.F('output_tokens') + usage_data.get('completion_tokens', 0),
            total_tokens=models.F('total_tokens') + usage_data.get('total_tokens', 0),
            daily_prompt_count=models.F('daily_prompt_count') + 1,
            daily_input_tokens=models.F('daily_input_tokens') + usage_data.get('prompt_tokens', 0),
            daily_output_tokens=models.F('daily_output_tokens') + usage_data.get('completion_tokens', 0),
        )

    @classmethod
    def check_quota(cls, user_id):
        """检查免费用户今日配额。返回 (ok: bool, error_msg: str)。"""
        cfg = SiteConfig.get()
        today = date.today()
        obj, _ = cls.objects.get_or_create(user_id=user_id)
        if obj.daily_date != today:
            return True, ''
        if obj.daily_prompt_count >= cfg.free_daily_prompt_count:
            return False, f'今日提交次数已达上限（{cfg.free_daily_prompt_count} 次），请明日再试'
        if obj.daily_input_tokens >= cfg.free_daily_input_tokens:
            return False, f'今日输入Token已达上限（{cfg.free_daily_input_tokens:,}），请明日再试'
        if obj.daily_output_tokens >= cfg.free_daily_output_tokens:
            return False, f'今日输出Token已达上限（{cfg.free_daily_output_tokens:,}），请明日再试'
        return True, ''


class SiteConfig(models.Model):
    """全局可配置参数（单例，仅允许一行）。"""
    code_cooldown_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name='发码冷却（秒）',
        help_text='同一邮箱两次发码的最短间隔，默认 300 秒（5 分钟）',
    )
    code_expire_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name='验证码有效期（分钟）',
        help_text='验证码从发出到失效的时间，默认 30 分钟',
    )
    code_daily_limit = models.PositiveIntegerField(
        default=100,
        verbose_name='全局每日发码上限',
        help_text='系统每自然日最多发送的验证码总次数，超出后当天无法新注册',
    )
    code_minute_limit = models.PositiveIntegerField(
        default=5,
        verbose_name='全局每分钟发码上限',
        help_text='全站每分钟最多发送的验证码次数，防止瞬时刷量',
    )
    # 免费用户每日 Token 配额
    free_daily_input_tokens = models.PositiveIntegerField(
        default=50000,
        verbose_name='免费用户每日输入Token上限',
        help_text='免费用户（未配置自己API密钥）每自然日最多消耗的输入Token数，默认 50,000',
    )
    free_daily_output_tokens = models.PositiveIntegerField(
        default=25000,
        verbose_name='免费用户每日输出Token上限',
        help_text='免费用户（未配置自己API密钥）每自然日最多消耗的输出Token数，默认 25,000',
    )
    free_daily_prompt_count = models.PositiveIntegerField(
        default=10,
        verbose_name='免费用户每日提交次数上限',
        help_text='免费用户每自然日最多提交的AI请求次数，默认 10 次',
    )
    # 网站品牌
    site_title = models.CharField(
        max_length=100,
        default='MineAI',
        verbose_name='网站标题',
        help_text='显示在浏览器标签页、导航栏和登录页的网站名称',
    )
    site_subtitle = models.CharField(
        max_length=200,
        default='多功能应用集成工作台',
        verbose_name='网站副标题',
        help_text='显示在登录页标题下方的描述文字',
    )
    site_favicon = models.CharField(
        max_length=500,
        blank=True,
        default='/static/favicon-mineai.svg',
        verbose_name='网站图标',
        help_text='浏览器标签页图标：填写图片URL（如 /static/favicon.ico）或直接填写 emoji（如 🚀）',
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name='最后修改时间')

    class Meta:
        verbose_name = '系统参数'
        verbose_name_plural = '系统参数'

    def save(self, *args, **kwargs):
        self.pk = 1  # 强制单例
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass  # 禁止删除

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        updates = []
        if (obj.site_title or '').strip() in ('', '应用平台'):
            obj.site_title = 'MineAI'
            updates.append('site_title')
        if not (obj.site_favicon or '').strip():
            obj.site_favicon = '/static/favicon-mineai.svg'
            updates.append('site_favicon')
        if updates:
            obj.save(update_fields=updates)
        return obj

    def __str__(self):
        return '系统参数'


class VerificationCode(models.Model):
    email = models.EmailField(verbose_name='邮箱', db_index=True)
    code = models.CharField(max_length=6, verbose_name='验证码')
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = '邮箱验证码'
        ordering = ['-created_at']

    @classmethod
    def generate(cls, email):
        code = f"{secrets.randbelow(1000000):06d}"
        cls.objects.create(email=email, code=code)
        return code

    @classmethod
    def cooldown_remaining(cls, email):
        """返回该邮箱还需等待的秒数，0 表示可以发送。"""
        cfg = SiteConfig.get()
        cutoff = timezone.now() - timedelta(seconds=cfg.code_cooldown_seconds)
        latest = cls.objects.filter(email=email, created_at__gte=cutoff).first()
        if not latest:
            return 0
        elapsed = (timezone.now() - latest.created_at).total_seconds()
        return max(0, int(cfg.code_cooldown_seconds - elapsed))

    @classmethod
    def check_global_limits(cls):
        """检查全局速率限制，返回 (ok: bool, error_msg: str)。"""
        cfg = SiteConfig.get()
        now = timezone.now()

        # 每分钟上限
        minute_ago = now - timedelta(seconds=60)
        if cls.objects.filter(created_at__gte=minute_ago).count() >= cfg.code_minute_limit:
            return False, '系统繁忙，请稍后再试'

        # 每日上限（自然日）
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        if cls.objects.filter(created_at__gte=today_start).count() >= cfg.code_daily_limit:
            return False, f'系统今日验证码已达上限（{cfg.code_daily_limit} 次），请明日再试'

        return True, ''

    @classmethod
    def verify(cls, email, code):
        """校验验证码，成功后标记为已使用。"""
        cfg = SiteConfig.get()
        cutoff = timezone.now() - timedelta(minutes=cfg.code_expire_minutes)
        obj = cls.objects.filter(
            email=email, code=code, is_used=False, created_at__gte=cutoff
        ).first()
        if obj:
            obj.is_used = True
            obj.save(update_fields=['is_used'])
            return True
        return False


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = '密码重置令牌'

    def is_valid(self):
        if self.is_used:
            return False
        return timezone.now() < self.created_at + timedelta(minutes=30)


def sha256_of_file(f):
    """Compute SHA-256 of an InMemoryUploadedFile / TemporaryUploadedFile."""
    h = hashlib.sha256()
    for chunk in f.chunks():
        h.update(chunk)
    f.seek(0)
    return h.hexdigest()


FILE_TYPE_CHOICES = [
    ('pdf', 'PDF'),
    ('image', '图片'),
    ('doc', '文档'),
    ('code', '代码'),
    ('other', '其他'),
]

EXT_TO_TYPE = {
    '.pdf': 'pdf',
    '.jpg': 'image', '.jpeg': 'image', '.png': 'image',
    '.gif': 'image', '.webp': 'image', '.bmp': 'image', '.svg': 'image',
    '.doc': 'doc', '.docx': 'doc', '.xls': 'doc', '.xlsx': 'doc',
    '.ppt': 'doc', '.pptx': 'doc', '.txt': 'doc', '.md': 'doc', '.csv': 'doc',
    '.py': 'code', '.js': 'code', '.ts': 'code', '.jsx': 'code', '.tsx': 'code',
    '.java': 'code', '.c': 'code', '.cpp': 'code', '.cc': 'code',
    '.h': 'code', '.hpp': 'code', '.go': 'code', '.rs': 'code',
    '.sh': 'code', '.bash': 'code', '.zsh': 'code', '.html': 'code',
    '.css': 'code', '.scss': 'code', '.json': 'code', '.yaml': 'code',
    '.yml': 'code', '.toml': 'code', '.xml': 'code', '.sql': 'code',
    '.r': 'code', '.rb': 'code', '.php': 'code', '.swift': 'code', '.kt': 'code',
}


class CloudFile(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cloud_files')
    name = models.CharField(max_length=255, verbose_name='文件名')
    size = models.PositiveBigIntegerField(verbose_name='文件大小（字节）')
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES, default='other', verbose_name='文件类型')
    file = models.FileField(upload_to=cloud_upload_path, verbose_name='文件')
    sha256 = models.CharField(max_length=64, blank=True, default='', verbose_name='SHA-256')
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='上传时间')

    class Meta:
        verbose_name = '云盘文件'
        verbose_name_plural = '云盘文件'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.user.email} – {self.name}'
