"""
tavern/views.py — SillyTavern 集成后端

功能：
1. status/     检查 ST 运行状态 + 当前用户账号信息
2. provision/  自动为当前 MineAI 用户创建 ST 账号（写文件系统）
3. admin/config/  管理员配置 ST 部署参数
4. admin/accounts/  管理员查看所有已预配账号
"""
import base64
import hashlib
import json
import os
import re
import secrets

import requests as _requests
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from core.auth import _token_auth
from .models import TavernAccount, TavernDeployment


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def _get_deployment():
    dep, _ = TavernDeployment.objects.get_or_create(pk=1)
    return dep


def _sanitize_handle(username: str) -> str:
    """将 MineAI 用户名转换为 SillyTavern handle（小写字母、数字、连字符）。"""
    handle = re.sub(r'[^a-z0-9-]', '-', username.lower())
    handle = re.sub(r'-+', '-', handle).strip('-')
    return (handle or 'user')[:50]


def _hash_password_st(password: str, salt: str | None = None):
    """
    用与 SillyTavern 完全相同的参数做 scrypt 哈希。
    ST 源码：crypto.scryptSync(password, salt, 64)  N=32768 r=8 p=1
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.scrypt(
        password.encode('utf-8'),
        salt=salt.encode('utf-8'),
        n=32768, r=8, p=1, dklen=64,
    )
    hashed = base64.b64encode(dk).decode('utf-8')
    return salt, hashed


def _create_user_in_fs(data_dir: str, handle: str, password: str, display_name: str) -> None:
    """
    直接在 SillyTavern 的 data 目录中创建用户。
    兼容 node-persist v3.x 默认存储格式（文件名 = key 字符串）。
    """
    storage_dir = os.path.join(data_dir, '_storage')
    os.makedirs(storage_dir, exist_ok=True)

    salt, hashed = _hash_password_st(password)

    user_record = {
        'handle': handle,
        'name': display_name,
        'password': hashed,
        'salt': salt,
        'admin': False,
        'enabled': True,
        'created': None,
    }
    # node-persist 文件格式：{"key": "...", "value": {...}}
    file_content = {'key': f'USERS.USER.{handle}', 'value': user_record}
    file_path = os.path.join(storage_dir, f'USERS.USER.{handle}')
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(file_content, f, ensure_ascii=False)

    # 创建用户数据目录（ST 首次登录时也会自动创建，但提前建好更稳妥）
    user_dir = os.path.join(data_dir, handle)
    for subdir in [
        'chats', 'characters', 'User Avatars', 'backgrounds',
        'worlds', 'themes', 'extensions', 'backups', 'group chats',
        os.path.join('user', 'images'), os.path.join('user', 'files'),
        'vectors', 'thumbnails',
        'NovelAI Settings', 'OpenAI Settings', 'TextGen Settings',
        'KoboldAI Settings',
    ]:
        os.makedirs(os.path.join(user_dir, subdir), exist_ok=True)


def _check_st_running(base_url: str) -> bool:
    try:
        r = _requests.get(f'{base_url}/api/ping', timeout=3)
        return r.status_code < 500
    except Exception:
        pass
    # 降级：尝试首页
    try:
        r = _requests.get(base_url, timeout=3)
        return r.status_code < 500
    except Exception:
        return False


# ── API 视图 ──────────────────────────────────────────────────────────────────

@csrf_exempt
def status(request):
    """GET /api/tavern/status/ — 返回 ST 状态 + 当前用户账号信息。"""
    user = _token_auth(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    dep = _get_deployment()
    running = _check_st_running(dep.base_url)

    account_info = None
    try:
        acct = TavernAccount.objects.get(user=user)
        account_info = {'handle': acct.handle, 'password': acct.password}
    except TavernAccount.DoesNotExist:
        pass

    return JsonResponse({
        'running': running,
        'url': dep.base_url,
        'allow_frame_embed': dep.allow_frame_embed,
        'data_dir_configured': bool(dep.data_dir),
        'setup_note': dep.setup_note,
        'provisioned': account_info is not None,
        'account': account_info,
    })


@csrf_exempt
def provision(request):
    """POST /api/tavern/provision/ — 为当前用户创建 SillyTavern 账号。"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    user = _token_auth(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    # 已存在则直接返回
    try:
        acct = TavernAccount.objects.get(user=user)
        acct.last_accessed = timezone.now()
        acct.save(update_fields=['last_accessed'])
        return JsonResponse({
            'ok': True,
            'handle': acct.handle,
            'password': acct.password,
            'existing': True,
        })
    except TavernAccount.DoesNotExist:
        pass

    dep = _get_deployment()
    if not dep.data_dir:
        return JsonResponse(
            {'error': '管理员尚未配置 SillyTavern 数据目录，暂无法自动创建账号，请联系管理员。'},
            status=503,
        )

    # 生成唯一 handle
    base_handle = _sanitize_handle(user.username)
    handle = base_handle
    suffix = 1
    while TavernAccount.objects.filter(handle=handle).exists():
        handle = f'{base_handle}-{suffix}'
        suffix += 1

    password = secrets.token_urlsafe(16)

    try:
        _create_user_in_fs(dep.data_dir, handle, password, user.username)
    except OSError as e:
        return JsonResponse({'error': f'写入用户文件失败：{e}'}, status=500)

    acct = TavernAccount.objects.create(
        user=user,
        handle=handle,
        password=password,
        last_accessed=timezone.now(),
    )

    return JsonResponse({
        'ok': True,
        'handle': acct.handle,
        'password': acct.password,
        'existing': False,
    })


@csrf_exempt
def admin_config(request):
    """GET/POST /api/tavern/admin/config/ — 管理员配置 ST 部署参数。"""
    user = _token_auth(request)
    if not user or not user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    dep = _get_deployment()

    if request.method == 'GET':
        return JsonResponse({
            'base_url': dep.base_url,
            'data_dir': dep.data_dir,
            'admin_handle': dep.admin_handle,
            'allow_frame_embed': dep.allow_frame_embed,
            'setup_note': dep.setup_note,
            'total_accounts': TavernAccount.objects.count(),
        })

    if request.method == 'POST':
        try:
            data = json.loads(request.body or b'{}')
        except ValueError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if 'base_url' in data:
            dep.base_url = data['base_url'].rstrip('/')
        if 'data_dir' in data:
            dep.data_dir = data['data_dir'].strip()
        if 'admin_handle' in data:
            dep.admin_handle = data['admin_handle'].strip()
        if 'allow_frame_embed' in data:
            dep.allow_frame_embed = bool(data['allow_frame_embed'])
        if 'setup_note' in data:
            dep.setup_note = data['setup_note']
        dep.save()
        return JsonResponse({'ok': True})

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def admin_accounts(request):
    """GET /api/tavern/admin/accounts/ — 管理员查看所有已预配账号。"""
    user = _token_auth(request)
    if not user or not user.is_staff:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    accounts = TavernAccount.objects.select_related('user').order_by('-provisioned_at')
    return JsonResponse({
        'accounts': [
            {
                'id': a.id,
                'username': a.user.username,
                'handle': a.handle,
                'provisioned_at': a.provisioned_at.isoformat(),
                'last_accessed': a.last_accessed.isoformat() if a.last_accessed else None,
            }
            for a in accounts
        ]
    })
