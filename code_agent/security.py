"""
代码助手 — 服务端文件上传安全校验模块
======================================
所有上传到服务器的代码文件必须经过此模块校验。
文件内容仅存储在 Django DB 的 CodeFile.content 文本字段中，
永远不会写入文件系统，永远不会被执行。
"""
import re
import unicodedata
from pathlib import Path
from django.conf import settings


# ──────────────────────────────────────────────
# 允许的代码文件扩展名白名单（仅文本类代码文件）
# ──────────────────────────────────────────────
ALLOWED_EXTENSIONS = {
    # Web
    '.html', '.htm', '.css', '.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte',
    '.mjs', '.cjs',
    # Python
    '.py', '.pyw', '.pyi',
    # Backend 语言
    '.rb', '.php', '.java', '.go', '.rs', '.cs', '.cpp', '.c', '.h', '.hpp',
    '.swift', '.kt', '.kts', '.scala', '.ex', '.exs', '.erl', '.hs', '.clj',
    '.lua', '.r', '.dart', '.nim', '.zig',
    # 数据 / 配置
    '.json', '.yaml', '.yml', '.toml', '.ini', '.xml', '.csv', '.tsv',
    '.sql', '.graphql', '.gql', '.proto', '.tf', '.hcl',
    # 文档
    '.md', '.txt', '.rst', '.org', '.adoc',
    # Shell / 脚本（只读，不执行）
    '.sh', '.bash', '.zsh', '.fish', '.ps1', '.bat', '.cmd',
    # 构建 / 配置
    '.dockerfile', '.makefile', '.mk', '.cmake', '.gradle',
    '.gitignore', '.gitattributes', '.editorconfig',
    '.prettierrc', '.eslintrc', '.babelrc', '.nvmrc',
    '.env.example', '.env.sample',
    # Jupyter
    '.ipynb',
    # 其他文本
    '.lock', '.sum', '.mod',
}

# 不带点的文件名白名单（如 Makefile, Dockerfile）
ALLOWED_BARE_NAMES = {
    'makefile', 'dockerfile', 'jenkinsfile', 'vagrantfile',
    'procfile', 'rakefile', 'gemfile', 'cmakelists.txt',
    '.gitignore', '.gitattributes', '.editorconfig', '.eslintrc',
    '.prettierrc', '.babelrc', '.nvmrc', '.npmrc',
}

# 禁止的路径模式
BLOCKED_PATH_PATTERNS = [
    r'\.\.[/\\]',          # 路径遍历 ../
    r'^[/\\]',             # 绝对路径
    r'\x00',               # null byte
    r'[<>:"|?*]',          # Windows 非法字符（跨平台保护）
]

# 可执行文件 magic bytes（base64 编码后的前几个字节）
# 用于检测二进制文件被 base64 编码后混入
BINARY_MAGIC_SIGNATURES = [
    b'\x7fELF',           # ELF 可执行文件（Linux）
    b'MZ',                # PE 可执行文件（Windows .exe/.dll）
    b'\xcf\xfa\xed\xfe',  # Mach-O 可执行文件（macOS 64-bit）
    b'\xce\xfa\xed\xfe',  # Mach-O 32-bit
    b'PK\x03\x04',        # ZIP 压缩包（.zip/.jar/.apk）
    b'\x1f\x8b',          # Gzip
    b'BZh',               # Bzip2
    b'\x89PNG',           # PNG 图片
    b'\xff\xd8\xff',      # JPEG 图片
    b'GIF8',              # GIF 图片
    b'%PDF',              # PDF
    b'{\rtf',             # RTF 文档
    b'\xd0\xcf\x11\xe0',  # MS Office 老格式
]

# 可疑的 LLM Prompt 注入模式（超长且异常的 system prompt 特征）
PROMPT_INJECTION_PATTERNS = [
    r'<\|system\|>',
    r'\[INST\].*\[/INST\]',
    r'<\|im_start\|>system',
    r'###\s*System\s*Prompt',
    r'IGNORE\s+ALL\s+PREVIOUS\s+INSTRUCTIONS',
    r'你现在是.{0,50}，忽略之前的所有指令',
]

_COMPILED_PATH_PATTERNS = [re.compile(p) for p in BLOCKED_PATH_PATTERNS]
_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE | re.DOTALL)
                                  for p in PROMPT_INJECTION_PATTERNS]


def _get_limits():
    return {
        'max_files': getattr(settings, 'CODE_AGENT_SERVER_UPLOAD_MAX_FILES', 100),
        'max_total_mb': getattr(settings, 'CODE_AGENT_SERVER_UPLOAD_MAX_TOTAL_MB', 50),
        'max_file_kb': getattr(settings, 'CODE_AGENT_SERVER_UPLOAD_MAX_FILE_KB', 1024),
    }


def validate_upload_file(path: str, content: str) -> dict:
    """
    对单个文件执行全量安全校验。

    Returns:
        {'valid': bool, 'reason': str, 'warning': str | None}
    """
    warning = None

    # 1. 路径长度
    if len(path) > 512:
        return {'valid': False, 'reason': '文件路径过长（> 512 字符）', 'warning': None}

    # 2. 路径遍历 / 非法字符
    for pattern in _COMPILED_PATH_PATTERNS:
        if pattern.search(path):
            return {'valid': False,
                    'reason': f'路径包含不安全字符或路径遍历尝试: {path!r}',
                    'warning': None}

    # 3. Unicode 路径规范化：拒绝含控制字符的路径
    for ch in path:
        cat = unicodedata.category(ch)
        if cat.startswith('C') and ch not in ('\t', '\n', '\r'):
            return {'valid': False, 'reason': '路径包含非法 Unicode 控制字符', 'warning': None}

    # 4. 扩展名白名单
    p = Path(path)
    ext = p.suffix.lower()
    bare_name = p.name.lower()

    if not ext and bare_name not in ALLOWED_BARE_NAMES:
        return {'valid': False,
                'reason': f'无扩展名文件 {bare_name!r} 不在允许列表中',
                'warning': None}
    if ext and ext not in ALLOWED_EXTENSIONS:
        return {'valid': False,
                'reason': f'文件扩展名 {ext!r} 不被支持（仅允许代码/文本类文件）',
                'warning': None}

    # 5. 单文件大小
    limits = _get_limits()
    max_bytes = limits['max_file_kb'] * 1024
    try:
        content_bytes = content.encode('utf-8')
    except (UnicodeEncodeError, AttributeError):
        return {'valid': False, 'reason': '文件内容不是有效 UTF-8 文本', 'warning': None}

    if len(content_bytes) > max_bytes:
        return {'valid': False,
                'reason': f'文件大小超过限制（{len(content_bytes) // 1024}KB > {limits["max_file_kb"]}KB）',
                'warning': None}

    # 6. 必须是有效 UTF-8（已由上一步保证，额外检查 decode 往返）
    try:
        content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        return {'valid': False, 'reason': '文件内容无法解析为 UTF-8 文本（可能是二进制文件）', 'warning': None}

    # 7. 二进制 magic bytes 检测（防止二进制文件被错误提交）
    raw_start = content_bytes[:16]
    for sig in BINARY_MAGIC_SIGNATURES:
        if raw_start.startswith(sig):
            return {'valid': False,
                    'reason': '检测到二进制/可执行文件特征，拒绝上传',
                    'warning': None}

    # 8. NULL byte 检测（对内容本身）
    if b'\x00' in content_bytes[:1024]:
        return {'valid': False,
                'reason': '文件内容包含 null byte，可能是二进制文件',
                'warning': None}

    # 9. Shell shebang 标记（允许查看但添加警告）
    first_line = content.split('\n', 1)[0].strip()
    if first_line.startswith('#!/'):
        warning = f'该文件包含 shebang 行 ({first_line[:60]})，已存储为只读代码，不会被执行'

    # 10. LLM Prompt 注入检测
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(content[:2000]):
            warning = (warning or '') + ' | 检测到可疑的 Prompt 注入模式，AI 处理时已标注'
            break

    return {'valid': True, 'reason': 'ok', 'warning': warning}


def validate_batch_upload(files_data: list, existing_file_count: int = 0) -> dict:
    """
    批量上传校验。

    Args:
        files_data: list of {'path': str, 'content': str}
        existing_file_count: 项目中已有的文件数

    Returns:
        {
            'allowed': [{'path', 'content', 'warning'}],
            'rejected': [{'path', 'reason'}],
            'error': str | None   # 整批拒绝时的原因
        }
    """
    limits = _get_limits()
    allowed = []
    rejected = []

    # 整批文件数量检查
    total_after = existing_file_count + len(files_data)
    if len(files_data) > limits['max_files']:
        return {
            'allowed': [],
            'rejected': [{'path': f['path'], 'reason': '超出批量上传文件数限制'} for f in files_data],
            'error': f'单次上传文件数 {len(files_data)} 超出限制 {limits["max_files"]}',
        }

    # 累计大小
    total_bytes = 0
    max_total_bytes = limits['max_total_mb'] * 1024 * 1024

    for item in files_data:
        path = item.get('path', '').strip().lstrip('/')
        content = item.get('content', '')

        if not path:
            rejected.append({'path': '(empty)', 'reason': '文件路径为空'})
            continue

        result = validate_upload_file(path, content)
        if not result['valid']:
            rejected.append({'path': path, 'reason': result['reason']})
            continue

        # 累计大小检查
        file_bytes = len(content.encode('utf-8'))
        total_bytes += file_bytes
        if total_bytes > max_total_bytes:
            rejected.append({'path': path, 'reason': f'累计总大小超出限制 {limits["max_total_mb"]}MB'})
            # 后续文件也全部拒绝
            remaining = files_data[files_data.index(item) + 1:]
            for r in remaining:
                rejected.append({'path': r.get('path', ''), 'reason': '累计总大小超出限制'})
            break

        allowed.append({'path': path, 'content': content, 'warning': result['warning']})

    return {'allowed': allowed, 'rejected': rejected, 'error': None}


def get_upload_limits() -> dict:
    """返回当前配置的上传限制（供前端展示）。"""
    limits = _get_limits()
    return {
        'max_files': limits['max_files'],
        'max_total_mb': limits['max_total_mb'],
        'max_file_kb': limits['max_file_kb'],
        'allowed_extensions': sorted(ALLOWED_EXTENSIONS),
    }
