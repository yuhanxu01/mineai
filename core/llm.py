import json
import urllib.request
import urllib.error
import urllib.error
from core.models import APIConfig, AgentLog


class _UserConfig:
    """Wraps a user's own API key with platform model/base settings."""
    def __init__(self, api_key, api_base, chat_model):
        self.api_key = api_key
        self.api_base = api_base
        self.chat_model = chat_model


def _get_config():
    from core.context import get_user
    user_id = get_user()
    if user_id:
        try:
            from accounts.models import User
            user = User.objects.get(id=user_id)
            if getattr(user, 'is_guest', False) and not user.user_api_key:
                raise ValueError("访客请先设置自己的API密钥，或登录使用平台密钥")
            if user.user_api_key:
                platform = APIConfig.get_active()
                return _UserConfig(
                    api_key=user.user_api_key,
                    api_base=platform.api_base if platform else 'https://open.bigmodel.cn/api/paas/v4',
                    chat_model=platform.chat_model if platform else 'glm-4.7-flash',
                )
        except Exception:
            pass
    config = APIConfig.get_active()
    if not config:
        raise ValueError("未配置API密钥，请在设置中添加您的API密钥，或联系管理员配置平台密钥")
    return config


def _api_call(endpoint, payload, config=None):
    if config is None:
        config = _get_config()
    url = f"{config.api_base}/{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config.api_key}',
    })
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        raise ValueError(f"GLM API错误 {e.code}: {body}")


def _check_quota(user_id, config):
    """免费用户（使用平台密钥）配额检查，超限时抛出 ValueError。"""
    if isinstance(config, _UserConfig):
        return  # 用户自带密钥，不受配额限制
    if not user_id:
        return
    try:
        from accounts.models import User, TokenUsage
        user = User.objects.get(id=user_id)
        if user.is_staff or user.is_superuser:
            return  # 管理员不受限
        ok, msg = TokenUsage.check_quota(user_id)
        if not ok:
            raise ValueError(msg)
    except ValueError:
        raise
    except Exception:
        pass


def chat(messages, system=None, temperature=0.7, max_tokens=4096, project_id=None):
    config = _get_config()
    from core.context import get_user
    _check_quota(get_user(), config)
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": config.chat_model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'调用 {config.chat_model}',
        content=msgs[-1]["content"][:200] if msgs else '',
        metadata={"model": config.chat_model, "tokens_limit": max_tokens}
    )

    result = _api_call('chat/completions', payload, config)
    text = result['choices'][0]['message']['content']
    usage = result.get('usage', {})

    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'响应完成 ({usage.get("total_tokens", "?")} tokens)',
        content=text[:500],
        metadata=usage
    )

    user_id = get_user()
    if user_id and usage:
        try:
            from accounts.models import TokenUsage
            TokenUsage.record(user_id, usage)
        except Exception:
            pass

    return text


def chat_stream(messages, system=None, temperature=0.7, max_tokens=4096,
                project_id=None, config=None, user_id=None):
    """
    流式版本的 chat()。生成器，逐块 yield 文本内容。
    config 和 user_id 应在视图中提前捕获并传入，避免 threading.local 上下文失效问题。
    """
    if config is None:
        config = _get_config()
    if user_id is None:
        from core.context import get_user
        user_id = get_user()

    _check_quota(user_id, config)

    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)

    payload = {
        "model": config.chat_model,
        "messages": msgs,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }

    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'调用(流式) {config.chat_model}',
        content=msgs[-1]["content"][:200] if msgs else '',
        metadata={"model": config.chat_model, "tokens_limit": max_tokens, "stream": True}
    )

    url = f"{config.api_base}/chat/completions"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {config.api_key}',
    })

    usage = {}
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode('utf-8').strip()
                if not line or not line.startswith('data: '):
                    continue
                data_str = line[6:]
                if data_str == '[DONE]':
                    break
                try:
                    chunk_data = json.loads(data_str)
                    delta = chunk_data['choices'][0].get('delta', {})
                    content = delta.get('content', '')
                    if content:
                        yield content
                    if chunk_data.get('usage'):
                        usage = chunk_data['usage']
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8') if e.fp else str(e)
        raise ValueError(f"GLM API错误 {e.code}: {body}")

    AgentLog.objects.create(
        project_id=project_id,
        level='llm',
        title=f'流式响应完成 ({usage.get("total_tokens", "?")} tokens)',
        content='',
        metadata=usage
    )

    if user_id and usage:
        try:
            from accounts.models import TokenUsage
            TokenUsage.record(user_id, usage)
        except Exception:
            pass
