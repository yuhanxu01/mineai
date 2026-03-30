import json
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from core.auth import _token_auth
from core.context import set_user
from .models import Plugin, PluginData
from .builtin_templates import LAN_TRANSFER_PLUGIN_HTML


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _json(data, status=200):
    return JsonResponse(data, status=status)


def _plugin_dict(plugin, include_html=False):
    author_name = getattr(plugin.author, 'email', None) or getattr(plugin.author, 'username', None) or str(plugin.author)
    d = {
        'id': plugin.pk,
        'name': plugin.name,
        'slug': plugin.slug,
        'description': plugin.description,
        'icon': plugin.icon,
        'color': plugin.color,
        'plugin_type': plugin.plugin_type,
        'config': plugin.config,
        'status': plugin.status,
        'is_public': plugin.is_public,
        'author': author_name,
        'author_id': plugin.author_id,
        'created_at': plugin.created_at.isoformat(),
    }
    if include_html:
        d['html_content'] = plugin.html_content
    return d


def _runtime_plugin_for_user(pk, user):
    """Plugin available in runtime: approved public OR owner/staff."""
    try:
        plugin = Plugin.objects.get(pk=pk)
    except Plugin.DoesNotExist:
        return None
    if plugin.status == Plugin.STATUS_APPROVED:
        return plugin
    if user and (user.pk == plugin.author_id or user.is_staff):
        return plugin
    return None


# ---------------------------------------------------------------------------
# Public: list approved plugins
# ---------------------------------------------------------------------------

@require_http_methods(['GET'])
def plugin_list(request):
    """GET /api/plugin/plugins/ — returns all approved public plugins."""
    plugins = Plugin.objects.filter(status=Plugin.STATUS_APPROVED, is_public=True)
    return _json({'plugins': [_plugin_dict(p) for p in plugins]})


# ---------------------------------------------------------------------------
# Authenticated: submit new plugin
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['POST'])
def plugin_create(request):
    """POST /api/plugin/plugins/ — submit a new plugin (pending review)."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    try:
        data = json.loads(request.body)
    except Exception:
        return _json({'error': 'Invalid JSON'}, 400)

    name = data.get('name', '').strip()
    if not name:
        return _json({'error': 'name required'}, 400)

    plugin_type = data.get('plugin_type', Plugin.TYPE_NOCODE)
    if plugin_type not in (Plugin.TYPE_CODE, Plugin.TYPE_NOCODE):
        return _json({'error': 'invalid plugin_type'}, 400)

    plugin = Plugin.objects.create(
        name=name,
        description=data.get('description', ''),
        icon=data.get('icon', 'puzzle'),
        color=data.get('color', '#c9a86c'),
        plugin_type=plugin_type,
        html_content=data.get('html_content', '') if plugin_type == Plugin.TYPE_CODE else '',
        config=data.get('config', {}),
        author=user,
        status=Plugin.STATUS_APPROVED if user.is_staff else Plugin.STATUS_PENDING,
        is_public=data.get('is_public', True),
    )
    return _json(_plugin_dict(plugin), 201)


# ---------------------------------------------------------------------------
# Plugin detail: GET / PUT / DELETE by author
# ---------------------------------------------------------------------------

@csrf_exempt
def plugin_detail(request, pk):
    """GET|PUT|DELETE /api/plugin/plugins/<pk>/"""
    try:
        plugin = Plugin.objects.get(pk=pk)
    except Plugin.DoesNotExist:
        return _json({'error': 'Not found'}, 404)

    if request.method == 'GET':
        # Public read for approved plugins; author can always read
        user = _token_auth(request)
        if plugin.status != Plugin.STATUS_APPROVED and (not user or user.pk != plugin.author_id):
            return _json({'error': 'Not found'}, 404)
        return _json(_plugin_dict(plugin, include_html=True))

    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    if request.method == 'PUT':
        if user.pk != plugin.author_id and not user.is_staff:
            return _json({'error': 'Forbidden'}, 403)
        try:
            data = json.loads(request.body)
        except Exception:
            return _json({'error': 'Invalid JSON'}, 400)

        for field in ('name', 'description', 'icon', 'color', 'config', 'html_content', 'is_public'):
            if field in data:
                setattr(plugin, field, data[field])
        # Re-submit resets to pending (unless admin)
        if not user.is_staff:
            plugin.status = Plugin.STATUS_PENDING
        plugin.save()
        return _json(_plugin_dict(plugin, include_html=True))

    if request.method == 'DELETE':
        if user.pk != plugin.author_id and not user.is_staff:
            return _json({'error': 'Forbidden'}, 403)
        plugin.delete()
        return _json({'deleted': True})

    return _json({'error': 'Method not allowed'}, 405)


# ---------------------------------------------------------------------------
# My plugins (author view)
# ---------------------------------------------------------------------------

@require_http_methods(['GET'])
def my_plugins(request):
    """GET /api/plugin/my/ — list caller's own plugins with status."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)
    plugins = Plugin.objects.filter(author=user)
    return _json({'plugins': [_plugin_dict(p) for p in plugins]})


@csrf_exempt
@require_http_methods(['POST'])
def plugin_visibility(request, pk):
    """POST /api/plugin/plugins/<pk>/visibility/ — owner toggles homepage visibility."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    try:
        plugin = Plugin.objects.get(pk=pk)
    except Plugin.DoesNotExist:
        return _json({'error': 'Not found'}, 404)

    if user.pk != plugin.author_id and not user.is_staff:
        return _json({'error': 'Forbidden'}, 403)

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        return _json({'error': 'Invalid JSON'}, 400)

    if 'is_public' not in data:
        return _json({'error': 'is_public required'}, 400)

    plugin.is_public = bool(data.get('is_public'))
    plugin.save(update_fields=['is_public', 'updated_at'])
    return _json({'ok': True, 'plugin': _plugin_dict(plugin)})


# ---------------------------------------------------------------------------
# Serve Code Plugin HTML (with injected SDK)
# ---------------------------------------------------------------------------

_SDK_TEMPLATE = """
<script>
(function(){
  var _pluginId = {plugin_id};
  var _origin = window.location.origin;
  var _pending = {{}};
  var _counter = 0;

  window.addEventListener('message', function(e){{
    if (e.origin !== _origin) return;
    var msg = e.data;
    if (!msg || !msg._mineai_reply) return;
    var cb = _pending[msg._req_id];
    if (cb) {{ cb(msg); delete _pending[msg._req_id]; }}
  }});

  function _send(type, payload){{
    return new Promise(function(resolve){{
      var id = ++_counter;
      _pending[id] = resolve;
      window.parent.postMessage(Object.assign({{_mineai: true, type: type, _req_id: id}}, payload), _origin);
    }});
  }}

  window.MineAI = {{
    callLLM: function(messages, onChunk){{
      return new Promise(function(resolve){{
        var id = ++_counter;
        window.parent.postMessage({{_mineai: true, type: 'LLM_REQUEST', _req_id: id,
          pluginId: _pluginId, messages: messages}}, _origin);
        var full = '';
        function handler(e){{
          if (e.origin !== _origin) return;
          var msg = e.data;
          if (!msg || !msg._mineai_reply || msg._req_id !== id) return;
          if (msg.chunk) {{ full += msg.chunk; if (onChunk) onChunk(msg.chunk); }}
          if (msg.done) {{ window.removeEventListener('message', handler); resolve(full); }}
        }}
        window.addEventListener('message', handler);
      }});
    }},
    getData: function(key){{
      return _send('DATA_GET', {{pluginId: _pluginId, key: key}}).then(function(r){{ return r.value; }});
    }},
    setData: function(key, value){{
      return _send('DATA_SET', {{pluginId: _pluginId, key: key, value: value}});
    }},
    getMemory: function(query){{
      return _send('MEMORY_GET', {{pluginId: _pluginId, query: query}}).then(function(r){{ return r.results; }});
    }},
  }};
}})();
</script>
"""


def plugin_serve(request, pk):
    """GET /api/plugin/<pk>/serve/ — serve Code Plugin HTML with SDK injected."""
    try:
        plugin = Plugin.objects.get(pk=pk, plugin_type=Plugin.TYPE_CODE)
    except Plugin.DoesNotExist:
        return HttpResponse('Not found', status=404)

    if plugin.status != Plugin.STATUS_APPROVED:
        user = _token_auth(request)
        if not user or (user.pk != plugin.author_id and not user.is_staff):
            return HttpResponse('Not available', status=403)

    sdk = _SDK_TEMPLATE.replace('{plugin_id}', str(plugin.pk))
    html = plugin.html_content

    # Inject SDK before closing </body> or at the start
    if '</body>' in html.lower():
        idx = html.lower().rfind('</body>')
        html = html[:idx] + sdk + html[idx:]
    elif '</head>' in html.lower():
        idx = html.lower().rfind('</head>')
        html = html[:idx] + sdk + html[idx:]
    else:
        html = sdk + html

    return HttpResponse(html, content_type='text/html; charset=utf-8')


# ---------------------------------------------------------------------------
# LLM Proxy (SSE)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['POST'])
def plugin_proxy_llm(request, pk):
    """POST /api/plugin/<pk>/proxy/llm/ — streams LLM response for a plugin."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    plugin = _runtime_plugin_for_user(pk, user)
    if not plugin:
        return _json({'error': 'Plugin not found or not available'}, 404)

    try:
        data = json.loads(request.body)
    except Exception:
        return _json({'error': 'Invalid JSON'}, 400)

    messages = data.get('messages', [])
    if not messages:
        return _json({'error': 'messages required'}, 400)

    # Prepend system prompt from No-Code plugin config if present
    system = None
    if plugin.plugin_type == Plugin.TYPE_NOCODE:
        system = plugin.config.get('system_prompt') or None

    from core.llm import chat_stream, _get_config
    from core.context import set_user

    set_user(user.pk)
    try:
        config = _get_config()
    except ValueError as e:
        return _json({'error': str(e)}, 400)

    def generator():
        try:
            for chunk in chat_stream(
                messages,
                system=system,
                project_id=plugin.memory_offset,
                config=config,
                user_id=user.pk,
            ):
                yield f'data: {json.dumps({"content": chunk})}\n\n'
        except Exception as e:
            yield f'data: {json.dumps({"error": str(e)})}\n\n'
        yield f'data: {json.dumps({"done": True})}\n\n'

    return StreamingHttpResponse(generator(), content_type='text/event-stream')


# ---------------------------------------------------------------------------
# Memory Proxy
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['POST'])
def plugin_proxy_memory(request, pk):
    """POST /api/plugin/<pk>/proxy/memory/ — retrieves context from memory pyramid."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    plugin = _runtime_plugin_for_user(pk, user)
    if not plugin:
        return _json({'error': 'Plugin not found'}, 404)

    try:
        data = json.loads(request.body)
    except Exception:
        return _json({'error': 'Invalid JSON'}, 400)

    query = data.get('query', '')
    if not query:
        return _json({'results': []})

    try:
        from memory.pyramid import retrieve_context
        results = retrieve_context(query, project_id=plugin.memory_offset)
        return _json({'results': results})
    except Exception as e:
        return _json({'error': str(e)}, 500)


# ---------------------------------------------------------------------------
# Plugin KV Data
# ---------------------------------------------------------------------------

@csrf_exempt
def plugin_data(request, pk):
    """GET|POST /api/plugin/<pk>/data/ — per-user KV storage."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    plugin = _runtime_plugin_for_user(pk, user)
    if not plugin:
        return _json({'error': 'Plugin not found'}, 404)

    if request.method == 'GET':
        items = PluginData.objects.filter(plugin=plugin, user=user)
        return _json({'data': {item.key: item.value for item in items}})

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception:
            return _json({'error': 'Invalid JSON'}, 400)
        key = data.get('key', '').strip()
        value = data.get('value', '')
        if not key:
            return _json({'error': 'key required'}, 400)
        PluginData.objects.update_or_create(
            plugin=plugin, user=user, key=key,
            defaults={'value': value}
        )
        return _json({'ok': True})

    return _json({'error': 'Method not allowed'}, 405)


# ---------------------------------------------------------------------------
# Admin: list pending
# ---------------------------------------------------------------------------

@require_http_methods(['GET'])
def admin_pending(request):
    """GET /api/plugin/admin/pending/ — list pending plugins (staff only)."""
    user = _token_auth(request)
    if not user or not user.is_staff:
        return _json({'error': 'Forbidden'}, 403)
    plugins = Plugin.objects.filter(status=Plugin.STATUS_PENDING)
    return _json({'plugins': [_plugin_dict(p, include_html=True) for p in plugins]})


# ---------------------------------------------------------------------------
# Admin: review (approve / reject)
# ---------------------------------------------------------------------------

@csrf_exempt
@require_http_methods(['POST'])
def admin_review(request, pk):
    """POST /api/plugin/admin/<pk>/review/ — approve or reject a plugin."""
    user = _token_auth(request)
    if not user or not user.is_staff:
        return _json({'error': 'Forbidden'}, 403)

    try:
        plugin = Plugin.objects.get(pk=pk)
    except Plugin.DoesNotExist:
        return _json({'error': 'Not found'}, 404)

    try:
        data = json.loads(request.body)
    except Exception:
        return _json({'error': 'Invalid JSON'}, 400)

    action = data.get('action')
    if action == 'approve':
        plugin.status = Plugin.STATUS_APPROVED
    elif action == 'reject':
        plugin.status = Plugin.STATUS_REJECTED
    else:
        return _json({'error': 'action must be approve or reject'}, 400)

    plugin.save()
    return _json(_plugin_dict(plugin))


@csrf_exempt
@require_http_methods(['POST'])
def install_lan_transfer_template(request):
    """Install or update an official LAN transfer code plugin for current user."""
    user = _token_auth(request)
    if not user:
        return _json({'error': 'Unauthorized'}, 401)

    plugin = Plugin.objects.filter(
        author=user,
        name='局域网大文件直传',
        plugin_type=Plugin.TYPE_CODE,
    ).first()

    if plugin:
        plugin.description = 'WebRTC 点对点传输 · 服务器仅信令中转 · 超大文件分片 · 局域网直连不占服务器带宽'
        plugin.icon = 'send'
        plugin.color = '#2f8cff'
        plugin.html_content = LAN_TRANSFER_PLUGIN_HTML
        plugin.is_public = True
        plugin.status = Plugin.STATUS_APPROVED
        plugin.config = {**(plugin.config or {}), 'official_template': 'lan_transfer'}
        plugin.save()
        return _json({'ok': True, 'plugin': _plugin_dict(plugin, include_html=True), 'updated': True})

    plugin = Plugin.objects.create(
        name='局域网大文件直传',
        description='WebRTC 点对点传输 · 服务器仅信令中转 · 超大文件分片 · 局域网直连不占服务器带宽',
        icon='send',
        color='#2f8cff',
        plugin_type=Plugin.TYPE_CODE,
        html_content=LAN_TRANSFER_PLUGIN_HTML,
        config={'official_template': 'lan_transfer'},
        author=user,
        status=Plugin.STATUS_APPROVED,
        is_public=True,
    )
    return _json({'ok': True, 'plugin': _plugin_dict(plugin, include_html=True), 'created': True}, 201)
