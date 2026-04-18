"""
SSH Manager views — stateless relay.
Credentials are passed in each request body and never persisted.
"""
import io
import json
import mimetypes
import os
import secrets
import select as _select
import shlex
import hashlib
import tempfile
import stat
import threading
import time
import zipfile

import paramiko
from django.http import FileResponse, HttpResponse, JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.auth import _token_auth

MAX_TEXT_SIZE = 512 * 1024      # 512 KB
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10 MB
MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
ZIP_SPOOL_LIMIT = 8 * 1024 * 1024
ZIP_MAX_FILES = int(os.environ.get('SSH_ZIP_MAX_FILES', '20000'))
ZIP_MAX_TOTAL_SIZE = int(os.environ.get('SSH_ZIP_MAX_TOTAL_SIZE_MB', '10240')) * 1024 * 1024
SSH_SESSION_TTL = int(os.environ.get('SSH_SESSION_TTL_SEC', '120'))

_SFTP_CACHE = {}
_SFTP_CACHE_LOCK = threading.Lock()

TERM_SESSION_TTL = int(os.environ.get('SSH_TERM_TTL_SEC', '1800'))  # 30 min idle
_TERM_SESSIONS: dict = {}
_TERM_LOCK = threading.Lock()


class _SFTPSessionProxy:
    def __init__(self, raw):
        self._raw = raw

    def close(self):
        # pooled session: request handlers should not tear it down every time
        return None

    def __getattr__(self, name):
        return getattr(self._raw, name)


class _SSHSessionProxy:
    def __init__(self, raw):
        self._raw = raw

    def close(self):
        return None

    def __getattr__(self, name):
        return getattr(self._raw, name)


def _close_cached_pair(ssh, sftp):
    try:
        if sftp:
            sftp.close()
    except Exception:
        pass
    try:
        if ssh:
            ssh.close()
    except Exception:
        pass


def _conn_cache_key(data: dict) -> str:
    basis = json.dumps({
        'host': data.get('host', '').strip(),
        'port': int(data.get('port', 22)),
        'username': data.get('username', '').strip(),
        'auth_type': data.get('auth_type', 'password'),
        'secret': data.get('secret', ''),
        'passphrase': data.get('passphrase', '') or '',
    }, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode('utf-8')).hexdigest()


def _prune_sftp_cache(force_key=None):
    now = time.time()
    stale = []
    with _SFTP_CACHE_LOCK:
        for key, item in list(_SFTP_CACHE.items()):
            transport = item['ssh'].get_transport() if item.get('ssh') else None
            expired = (now - item.get('last_used', 0)) > SSH_SESSION_TTL
            dead = not transport or not transport.is_active()
            if key == force_key or expired or dead:
                stale.append(_SFTP_CACHE.pop(key))
    for item in stale:
        _close_cached_pair(item.get('ssh'), item.get('sftp'))


def _build_ssh_connect_kwargs(data: dict):
    host = data.get('host', '').strip()
    port = int(data.get('port', 22))
    username = data.get('username', '').strip()
    auth_type = data.get('auth_type', 'password')
    secret = data.get('secret', '')
    passphrase = data.get('passphrase', '') or None

    kwargs = dict(
        hostname=host,
        port=port,
        username=username,
        timeout=10,
        banner_timeout=10,
        auth_timeout=10,
        allow_agent=False,
        look_for_keys=False,
    )
    if auth_type == 'key':
        for key_cls in (paramiko.RSAKey, paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.DSSKey):
            try:
                pkey = key_cls.from_private_key(io.StringIO(secret), password=passphrase)
                kwargs['pkey'] = pkey
                break
            except Exception:
                continue
        else:
            raise paramiko.SSHException('Unsupported or invalid private key format')
    else:
        kwargs['password'] = secret
    return kwargs


def _connect_ssh_client(data: dict):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(**_build_ssh_connect_kwargs(data))
    transport = ssh.get_transport()
    if transport:
        transport.set_keepalive(30)
    return ssh


def _get_sftp(data: dict):
    """Open or reuse a short-lived pooled paramiko SFTP channel."""
    cache_key = _conn_cache_key(data)
    _prune_sftp_cache()
    with _SFTP_CACHE_LOCK:
        cached = _SFTP_CACHE.get(cache_key)
        if cached:
            transport = cached['ssh'].get_transport() if cached.get('ssh') else None
            if transport and transport.is_active():
                cached['last_used'] = time.time()
                return _SSHSessionProxy(cached['ssh']), _SFTPSessionProxy(cached['sftp'])

    ssh = _connect_ssh_client(data)
    sftp = ssh.open_sftp()
    with _SFTP_CACHE_LOCK:
        old = _SFTP_CACHE.pop(cache_key, None)
        _SFTP_CACHE[cache_key] = {'ssh': ssh, 'sftp': sftp, 'last_used': time.time()}
    if old:
        _close_cached_pair(old.get('ssh'), old.get('sftp'))
    return _SSHSessionProxy(ssh), _SFTPSessionProxy(sftp)


def _sftp_error(e):
    if isinstance(e, paramiko.AuthenticationException):
        return Response({'error': f'认证失败: {e}'}, status=401)
    if isinstance(e, paramiko.SSHException):
        return Response({'error': f'SSH 错误: {e}'}, status=502)
    if isinstance(e, (FileNotFoundError, IOError)) and getattr(e, 'errno', None) == 2:
        return Response({'error': '文件/目录不存在'}, status=404)
    if isinstance(e, PermissionError):
        return Response({'error': '权限不足'}, status=403)
    return Response({'error': str(e)}, status=500)


def _parse_body(request):
    try:
        return json.loads(request.body or b'{}')
    except Exception:
        return {}


def _fmt_size(n):
    if n is None:
        return ''
    if n >= 1024 * 1024:
        return f'{n / 1024 / 1024:.1f}M'
    if n >= 1024:
        return f'{n / 1024:.1f}K'
    return str(n)


def _makedirs_sftp(sftp, remote_dir: str):
    """Recursively create remote directories, silently skip if they already exist."""
    parts = [p for p in remote_dir.split('/') if p]
    current = '/'
    for part in parts:
        current = current.rstrip('/') + '/' + part
        try:
            sftp.stat(current)
        except IOError:
            try:
                sftp.mkdir(current)
            except Exception:
                pass  # already exists or permission denied — proceed


def _iter_sftp_chunks(sftp, remote_path, chunk_size=64 * 1024):
    with sftp.open(remote_path, 'rb') as src:
        while True:
            chunk = src.read(chunk_size)
            if not chunk:
                break
            yield chunk


def _zip_collect_meta(sftp, remote_path, depth=0, totals=None):
    if totals is None:
        totals = {'files': 0, 'dirs': 0, 'bytes': 0}
    if depth > 20:
        return totals

    attrs = sftp.listdir_attr(remote_path)
    totals['dirs'] += 1
    for a in attrs:
        full = remote_path.rstrip('/') + '/' + a.filename
        if stat.S_ISDIR(a.st_mode):
            _zip_collect_meta(sftp, full, depth + 1, totals)
        else:
            totals['files'] += 1
            totals['bytes'] += a.st_size or 0
            if totals['files'] > ZIP_MAX_FILES:
                raise ValueError(f'打包文件数超过限制（>{ZIP_MAX_FILES}），请分批下载或调大 SSH_ZIP_MAX_FILES')
            if totals['bytes'] > ZIP_MAX_TOTAL_SIZE:
                raise ValueError(f'打包总大小超过限制（>{_fmt_size(ZIP_MAX_TOTAL_SIZE)}），请分批下载或调大 SSH_ZIP_MAX_TOTAL_SIZE_MB')
    return totals



def _perm(st_mode):
    s = ''
    for bit, ch in [
        (stat.S_IRUSR, 'r'), (stat.S_IWUSR, 'w'), (stat.S_IXUSR, 'x'),
        (stat.S_IRGRP, 'r'), (stat.S_IWGRP, 'w'), (stat.S_IXGRP, 'x'),
        (stat.S_IROTH, 'r'), (stat.S_IWOTH, 'w'), (stat.S_IXOTH, 'x'),
    ]:
        s += ch if st_mode & bit else '-'
    prefix = 'd' if stat.S_ISDIR(st_mode) else ('l' if stat.S_ISLNK(st_mode) else '-')
    return prefix + s


class TestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        ssh = sftp = None
        try:
            import time
            t0 = time.time()
            ssh, sftp = _get_sftp(data)
            ms = int((time.time() - t0) * 1000)
            return Response({'ok': True, 'latency_ms': ms})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class LsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '/') or '/'
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            attrs = sftp.listdir_attr(path)
            entries = []
            for a in attrs:
                mode = a.st_mode or 0
                if stat.S_ISDIR(mode):
                    is_dir = True
                elif stat.S_ISLNK(mode):
                    # Follow symlink to determine real type
                    try:
                        real = sftp.stat(path.rstrip('/') + '/' + a.filename)
                        is_dir = stat.S_ISDIR(real.st_mode) if real.st_mode else False
                    except Exception:
                        is_dir = False
                else:
                    is_dir = False
                entries.append({
                    'name': a.filename,
                    'path': path.rstrip('/') + '/' + a.filename,
                    'is_dir': is_dir,
                    'size': a.st_size,
                    'size_str': _fmt_size(a.st_size) if not is_dir else '',
                    'mtime': a.st_mtime,
                    'perm': _perm(mode) if mode else '',
                    'is_link': stat.S_ISLNK(mode),
                })
            entries.sort(key=lambda x: (not x['is_dir'], x['name'].lower()))
            return Response({'path': path, 'entries': entries})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class ReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            size = sftp.stat(path).st_size
            if size > MAX_TEXT_SIZE:
                return Response({'too_large': True, 'size': size, 'path': path})
            with sftp.open(path, 'r') as f:
                content = f.read()
            text = content.decode('utf-8', errors='replace')
            return Response({'content': text, 'size': size, 'path': path})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class WriteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        content = data.get('content', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            encoded = content.encode('utf-8')
            with sftp.open(path, 'w') as f:
                f.write(encoded)
            return Response({'ok': True, 'size': len(encoded)})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class UploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        conn_json = request.POST.get('conn', '{}')
        remote_path = request.POST.get('remote_path', '')
        # conflict_mode:
        #   'replace' (default) — overwrite if exists
        #   'skip'              — skip silently if exists, upload if not
        #   'check'             — only stat, return {exists: bool}, never upload
        conflict_mode = request.POST.get('conflict_mode', 'replace')
        uploaded = request.FILES.get('file')
        if not remote_path:
            return Response({'error': '缺少参数'}, status=400)
        if conflict_mode == 'replace' and not uploaded:
            return Response({'error': '缺少文件'}, status=400)
        try:
            data = json.loads(conn_json)
        except Exception:
            return Response({'error': '连接参数无效'}, status=400)

        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)

            # 'check' — just report existence, never upload
            if conflict_mode == 'check':
                try:
                    sftp.stat(remote_path)
                    return Response({'exists': True})
                except FileNotFoundError:
                    return Response({'exists': False})

            # Auto-create parent directories
            parent_dir = '/'.join(remote_path.rstrip('/').split('/')[:-1])
            if parent_dir:
                _makedirs_sftp(sftp, parent_dir)

            # 'skip' — skip if exists
            if conflict_mode == 'skip':
                try:
                    sftp.stat(remote_path)
                    return Response({'ok': True, 'skipped': True})
                except FileNotFoundError:
                    pass

            if not uploaded:
                return Response({'error': '缺少文件'}, status=400)
            sftp.putfo(uploaded, remote_path)
            size = sftp.stat(remote_path).st_size
            return Response({'ok': True, 'path': remote_path, 'size': size})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class DownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            size = sftp.stat(path).st_size
            if size > MAX_DOWNLOAD_SIZE:
                return Response({'error': f'文件过大 ({_fmt_size(size)})，超过 50MB 限制'}, status=413)
            buf = io.BytesIO()
            sftp.getfo(path, buf)
            buf.seek(0)
            filename = path.split('/')[-1]
            resp = HttpResponse(buf.read(), content_type='application/octet-stream')
            resp['Content-Disposition'] = f'attachment; filename="{filename}"'
            return resp
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


@method_decorator(csrf_exempt, name='dispatch')
class ProxyView(View):
    """Image proxy — credentials in POST body, returns binary image data."""

    def post(self, request):
        user = _token_auth(request)
        if not user:
            return HttpResponse('Unauthorized', status=401)

        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return HttpResponse('Bad request', status=400)

        path = data.get('path', '')
        mime_type, _ = mimetypes.guess_type(path)
        if not mime_type or not mime_type.startswith('image/'):
            return HttpResponse('Not an image', status=403)

        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            size = sftp.stat(path).st_size
            if size > MAX_IMAGE_SIZE:
                return HttpResponse('Image too large', status=413)
            buf = io.BytesIO()
            sftp.getfo(path, buf)
            buf.seek(0)
            return HttpResponse(buf.read(), content_type=mime_type)
        except Exception as e:
            return HttpResponse(str(e), status=502)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


def _rmtree_sftp(sftp, path, depth=0):
    """递归删除远程目录及其全部内容（等价于 rm -rf）。"""
    if depth > 50:
        raise RecursionError('目录层级过深（>50），终止删除')
    try:
        attrs = sftp.listdir_attr(path)
    except IOError:
        # 不是目录或已不存在，直接尝试删文件
        sftp.remove(path)
        return
    for a in attrs:
        child = path.rstrip('/') + '/' + a.filename
        if stat.S_ISDIR(a.st_mode if a.st_mode else 0):
            _rmtree_sftp(sftp, child, depth + 1)
        else:
            sftp.remove(child)
    sftp.rmdir(path)


class DeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        is_dir = data.get('is_dir', False)
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            if is_dir:
                _rmtree_sftp(sftp, path)   # 递归删除，支持非空目录
            else:
                sftp.remove(path)
            return Response({'ok': True})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class MkdirView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            sftp.mkdir(path)
            return Response({'ok': True, 'path': path})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class RenameView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        old_path = data.get('old_path', '')
        new_path = data.get('new_path', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            sftp.rename(old_path, new_path)
            return Response({'ok': True})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


def _zip_add(sftp, remote_path, zf, arc_prefix='', depth=0):
    """递归把 remote_path 下所有内容加入 ZipFile，深度上限 20。"""
    if depth > 20:
        return 0
    attrs = sftp.listdir_attr(remote_path)
    added = 0
    if arc_prefix:
        zf.writestr(arc_prefix.rstrip('/') + '/', b'')
    for a in attrs:
        full = remote_path.rstrip('/') + '/' + a.filename
        arc  = (arc_prefix + '/' + a.filename).lstrip('/')
        if stat.S_ISDIR(a.st_mode):
            added += _zip_add(sftp, full, zf, arc, depth + 1)
        else:
            with zf.open(arc, 'w') as dst:
                for chunk in _iter_sftp_chunks(sftp, full):
                    dst.write(chunk)
            added += 1
    return added


def _copy_remote(sftp, src, dst, depth=0):
    if depth > 20:
        raise ValueError('复制目录层级过深（>20）')
    attr = sftp.stat(src)
    if stat.S_ISDIR(attr.st_mode):
        try:
            sftp.mkdir(dst)
        except IOError:
            pass
        for child in sftp.listdir_attr(src):
            child_src = src.rstrip('/') + '/' + child.filename
            child_dst = dst.rstrip('/') + '/' + child.filename
            _copy_remote(sftp, child_src, child_dst, depth + 1)
        return {'files': 0, 'dirs': 1}

    with sftp.open(src, 'rb') as rf, sftp.open(dst, 'wb') as wf:
        while True:
            chunk = rf.read(64 * 1024)
            if not chunk:
                break
            wf.write(chunk)
    return {'files': 1, 'dirs': 0}


class ZipMetaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        paths = data.get('paths', [])
        if not paths:
            return Response({'error': '未指定路径'}, status=400)

        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            totals = {'files': 0, 'dirs': 0, 'bytes': 0}
            missing = []
            for path in paths:
                try:
                    a = sftp.stat(path)
                    if stat.S_ISDIR(a.st_mode):
                        _zip_collect_meta(sftp, path, totals=totals)
                    else:
                        totals['files'] += 1
                        totals['bytes'] += a.st_size or 0
                        if totals['files'] > ZIP_MAX_FILES:
                            raise ValueError(f'打包文件数超过限制（>{ZIP_MAX_FILES}），请分批下载或调大 SSH_ZIP_MAX_FILES')
                        if totals['bytes'] > ZIP_MAX_TOTAL_SIZE:
                            raise ValueError(f'打包总大小超过限制（>{_fmt_size(ZIP_MAX_TOTAL_SIZE)}），请分批下载或调大 SSH_ZIP_MAX_TOTAL_SIZE_MB')
                except FileNotFoundError:
                    missing.append(path)
            if totals['files'] == 0 and totals['dirs'] == 0:
                return Response({'error': '未找到可打包的文件或目录'}, status=404)
            return Response({
                'ok': True,
                'files': totals['files'],
                'dirs': totals['dirs'],
                'bytes': totals['bytes'],
                'bytes_str': _fmt_size(totals['bytes']),
                'missing': missing[:20],
            })
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class ZipDownloadView(APIView):
    """
    POST body: {...conn, paths: ['/a/file.py', '/b/dir'], zip_name: 'download.zip'}
    paths 可以是文件或目录，目录会被递归打包。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        paths = data.get('paths', [])
        zip_name = data.get('zip_name', 'download.zip') or 'download.zip'
        if not paths:
            return Response({'error': '未指定路径'}, status=400)

        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            spool = tempfile.SpooledTemporaryFile(max_size=ZIP_SPOOL_LIMIT, mode='w+b')
            added = 0
            with zipfile.ZipFile(spool, 'w', zipfile.ZIP_DEFLATED, allowZip64=True) as zf:
                for path in paths:
                    a = sftp.stat(path)
                    name = path.rstrip('/').split('/')[-1]
                    if stat.S_ISDIR(a.st_mode):
                        added += _zip_add(sftp, path, zf, name)
                    else:
                        with zf.open(name, 'w') as dst:
                            for chunk in _iter_sftp_chunks(sftp, path):
                                dst.write(chunk)
                        added += 1
            if added == 0:
                spool.close()
                return Response({'error': '没有可打包的文件，可能目录为空或路径无效'}, status=400)
            spool.seek(0)
            return FileResponse(spool, content_type='application/zip', as_attachment=True, filename=zip_name)
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


# ─── SSH-only helper (no SFTP channel needed for exec) ───────────────────────
def _get_ssh(data: dict):
    """Return an SSH client for exec, reusing the SFTP pool connection when available.

    SSH multiplexes channels over one transport, so exec and SFTP can share the
    same underlying connection.  The returned object may be a _SSHSessionProxy
    (cached, close() is a no-op) or a plain SSHClient (caller must close it).
    """
    cache_key = _conn_cache_key(data)
    with _SFTP_CACHE_LOCK:
        cached = _SFTP_CACHE.get(cache_key)
        if cached:
            transport = cached['ssh'].get_transport() if cached.get('ssh') else None
            if transport and transport.is_active():
                cached['last_used'] = time.time()
                return _SSHSessionProxy(cached['ssh'])  # no-op close, shared transport

    # No live cached connection — create a fresh one and register it in the pool
    # so the next SFTP *or* exec call can reuse it.
    ssh = _connect_ssh_client(data)
    sftp = ssh.open_sftp()
    with _SFTP_CACHE_LOCK:
        old = _SFTP_CACHE.pop(cache_key, None)
        _SFTP_CACHE[cache_key] = {'ssh': ssh, 'sftp': sftp, 'last_used': time.time()}
    if old:
        _close_cached_pair(old.get('ssh'), old.get('sftp'))
    return _SSHSessionProxy(ssh)  # no-op close, connection now owned by pool


@method_decorator(csrf_exempt, name='dispatch')
class ExecView(View):
    """
    POST body: {...conn, command: "ls -la", cwd: "/home/user"}
    SSE stream: {out: "..."} … {done: true, exit_code: N}
    """
    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({'error': 'Bad request'}, status=400)

        command = data.get('command', '').strip()
        cwd = data.get('cwd', '/') or '/'
        if not command:
            return JsonResponse({'error': '命令不能为空'}, status=400)

        inner_cmd = 'cd {} 2>/dev/null; {}'.format(shlex.quote(cwd), command)
        full_cmd = 'bash -c {}'.format(shlex.quote(inner_cmd))

        def generate():
            ssh = None
            try:
                ssh = _get_ssh(data)
                _, stdout, _ = ssh.exec_command(full_cmd, timeout=120, get_pty=True)
                channel = stdout.channel
                channel.setblocking(False)
                while True:
                    r, _, _ = _select.select([channel], [], [], 0.05)
                    if r:
                        chunk = channel.recv(4096)
                        if not chunk:
                            break
                        text = chunk.decode('utf-8', errors='replace')
                        yield 'data: {}\n\n'.format(json.dumps({'out': text}))
                    if channel.exit_status_ready() and not channel.recv_ready():
                        break
                exit_code = channel.recv_exit_status()
                yield 'data: {}\n\n'.format(json.dumps({'done': True, 'exit_code': exit_code}))
            except Exception as e:
                yield 'data: {}\n\n'.format(json.dumps({'error': str(e)}))
            finally:
                if ssh:
                    try: ssh.close()
                    except Exception: pass

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


class ChmodView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        path = data.get('path', '')
        mode_str = str(data.get('mode', '755'))
        ssh = sftp = None
        try:
            mode = int(mode_str, 8)
        except ValueError:
            return Response({'error': '无效权限值，请使用八进制如 755'}, status=400)
        try:
            ssh, sftp = _get_sftp(data)
            sftp.chmod(path, mode)
            new_attr = sftp.stat(path)
            return Response({'ok': True, 'perm': _perm(new_attr.st_mode)})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


class CopyView(APIView):
    """Server-side file/dir copy."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = _parse_body(request)
        src = data.get('src', '')
        dst = data.get('dst', '')
        ssh = sftp = None
        try:
            ssh, sftp = _get_sftp(data)
            stats = _copy_remote(sftp, src, dst)
            return Response({'ok': True, **stats})
        except Exception as e:
            return _sftp_error(e)
        finally:
            if sftp:
                try: sftp.close()
                except Exception: pass
            if ssh:
                try: ssh.close()
                except Exception: pass


# ─── Persistent PTY terminal sessions ────────────────────────────────────────

def _prune_term_sessions():
    now = time.time()
    stale = []
    with _TERM_LOCK:
        for sid, sess in list(_TERM_SESSIONS.items()):
            ch = sess.get('channel')
            expired = (now - sess.get('last_used', 0)) > TERM_SESSION_TTL
            dead = not ch or ch.closed
            if not dead:
                t = ch.get_transport() if hasattr(ch, 'get_transport') else None
                dead = not t or not t.is_active()
            if expired or dead:
                stale.append(_TERM_SESSIONS.pop(sid))
    for sess in stale:
        try: sess['channel'].close()
        except Exception: pass
        try:
            if sess.get('ssh'):
                sess['ssh'].close()
        except Exception:
            pass


@method_decorator(csrf_exempt, name='dispatch')
class TermOpenView(View):
    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({'error': 'Bad request'}, status=400)

        cols = int(data.get('cols', 200))
        rows = int(data.get('rows', 50))
        _prune_term_sessions()
        try:
            ssh = _connect_ssh_client(data)
            channel = ssh.invoke_shell(term='xterm-256color', width=cols, height=rows)
            channel.setblocking(False)
            session_id = secrets.token_hex(16)
            with _TERM_LOCK:
                _TERM_SESSIONS[session_id] = {
                    'ssh': ssh,
                    'channel': channel,
                    'user_id': user.id,
                    'last_used': time.time(),
                }
            return JsonResponse({'session_id': session_id})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


@method_decorator(csrf_exempt, name='dispatch')
class TermInputView(View):
    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({'error': 'Bad request'}, status=400)

        session_id = data.get('session_id', '')
        text = data.get('text', '')
        with _TERM_LOCK:
            sess = _TERM_SESSIONS.get(session_id)
        if not sess or sess['user_id'] != user.id:
            return JsonResponse({'error': 'Session not found'}, status=404)
        try:
            sess['channel'].sendall(text.encode('utf-8'))
            sess['last_used'] = time.time()
            return JsonResponse({'ok': True})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


@method_decorator(csrf_exempt, name='dispatch')
class TermResizeView(View):
    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({'error': 'Bad request'}, status=400)

        session_id = data.get('session_id', '')
        cols = max(20, int(data.get('cols', 120) or 120))
        rows = max(5, int(data.get('rows', 36) or 36))
        with _TERM_LOCK:
            sess = _TERM_SESSIONS.get(session_id)
        if not sess or sess['user_id'] != user.id:
            return JsonResponse({'error': 'Session not found'}, status=404)
        try:
            sess['channel'].resize_pty(width=cols, height=rows)
            sess['last_used'] = time.time()
            return JsonResponse({'ok': True, 'cols': cols, 'rows': rows})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=502)


@method_decorator(csrf_exempt, name='dispatch')
class TermStreamView(View):
    def get(self, request, session_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        with _TERM_LOCK:
            sess = _TERM_SESSIONS.get(session_id)
        if not sess or sess['user_id'] != user.id:
            return JsonResponse({'error': 'Session not found'}, status=404)

        channel = sess['channel']

        def generate():
            while True:
                try:
                    r, _, _ = _select.select([channel], [], [], 0.1)
                except Exception:
                    yield 'data: {}\n\n'.format(json.dumps({'closed': True}))
                    break
                if r:
                    try:
                        chunk = channel.recv(4096)
                    except Exception:
                        yield 'data: {}\n\n'.format(json.dumps({'closed': True}))
                        break
                    if not chunk:
                        yield 'data: {}\n\n'.format(json.dumps({'closed': True}))
                        break
                    text = chunk.decode('utf-8', errors='replace')
                    yield 'data: {}\n\n'.format(json.dumps({'out': text}))
                    with _TERM_LOCK:
                        if session_id in _TERM_SESSIONS:
                            _TERM_SESSIONS[session_id]['last_used'] = time.time()
                else:
                    t = channel.get_transport() if hasattr(channel, 'get_transport') else None
                    if channel.closed or not t or not t.is_active():
                        yield 'data: {}\n\n'.format(json.dumps({'closed': True}))
                        break

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


@method_decorator(csrf_exempt, name='dispatch')
class TermCloseView(View):
    def post(self, request):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': 'Unauthorized'}, status=401)
        try:
            data = json.loads(request.body or b'{}')
        except Exception:
            return JsonResponse({'error': 'Bad request'}, status=400)

        session_id = data.get('session_id', '')
        with _TERM_LOCK:
            sess = _TERM_SESSIONS.pop(session_id, None)
        if sess and sess['user_id'] == user.id:
            try: sess['channel'].close()
            except Exception: pass
            try:
                if sess.get('ssh'):
                    sess['ssh'].close()
            except Exception:
                pass
        return JsonResponse({'ok': True})
