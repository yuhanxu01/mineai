"""
生产环境设置 —— 通过环境变量覆盖开发配置中的敏感项。
使用方式：DJANGO_SETTINGS_MODULE=memoryforge.settings_prod
"""
import os
from .settings import *  # noqa: F401,F403

# ── 安全 ──────────────────────────────────────────────────────
SECRET_KEY = os.environ['SECRET_KEY']          # 必须设置，否则启动报错
DEBUG = False
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# ── HTTPS / 代理 ──────────────────────────────────────────────
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = int(os.environ.get('SECURE_HSTS_SECONDS', 31536000))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ── CORS（只允许自己的域名）──────────────────────────────────
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
] or [f"https://{h}" for h in ALLOWED_HOSTS if h]

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# ── 静态文件 ──────────────────────────────────────────────────
STATIC_ROOT = BASE_DIR / 'staticfiles'  # noqa: F405

# ── 邮件 ──────────────────────────────────────────────────────
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', EMAIL_HOST_USER)   # noqa: F405
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# ── 站点 URL ──────────────────────────────────────────────────
SITE_URL = os.environ.get('SITE_URL', 'https://your-domain.com')

# ── 日志 ──────────────────────────────────────────────────────
os.makedirs(BASE_DIR / 'logs', exist_ok=True)  # noqa: F405

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{asctime} {levelname} {name} {message}', 'style': '{'},
    },
    'handlers': {
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',  # noqa: F405
            'maxBytes': 10 * 1024 * 1024,
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['file', 'console'], 'level': 'WARNING'},
    'loggers': {
        'django': {'handlers': ['file', 'console'], 'level': 'WARNING', 'propagate': False},
    },
}
