import random
from datetime import timedelta

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


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, verbose_name='邮箱')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
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


class TokenUsage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='token_usage')
    prompt_count = models.PositiveIntegerField(default=0, verbose_name='提交次数')
    input_tokens = models.BigIntegerField(default=0, verbose_name='输入Token')
    output_tokens = models.BigIntegerField(default=0, verbose_name='输出Token')
    total_tokens = models.BigIntegerField(default=0, verbose_name='总Token')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Token用量'

    @classmethod
    def record(cls, user_id, usage_data):
        cls.objects.get_or_create(user_id=user_id)
        cls.objects.filter(user_id=user_id).update(
            prompt_count=models.F('prompt_count') + 1,
            input_tokens=models.F('input_tokens') + usage_data.get('prompt_tokens', 0),
            output_tokens=models.F('output_tokens') + usage_data.get('completion_tokens', 0),
            total_tokens=models.F('total_tokens') + usage_data.get('total_tokens', 0),
        )


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
        code = f"{random.randint(0, 999999):06d}"
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
