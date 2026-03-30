import json
import threading
import time
import urllib.request

from django.db.models import Count, Q, Sum
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import BridgeConnection, BridgeSession, BridgeMessage, PendingPermission, PendingCommand

TERMINAL_STATUSES = ('completed', 'error', 'cancelled')


def token_auth_user(request):
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Token '):
        return None
    try:
        from rest_framework.authtoken.models import Token
        return Token.objects.select_related('user').get(key=auth[6:].strip()).user
    except Exception:
        return None


def _next_seq(session):
    last = BridgeMessage.objects.filter(session=session).order_by('-seq').first()
    return (last.seq + 1) if last else 0


def _fire_webhook(webhook_url: str, payload: dict):
    """POST task completion data to webhook URL in a background thread."""
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webhook_url, data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'MineAI-Bridge/2.0'},
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass


def _session_to_dict(s, include_messages=False):
    d = {
        'id': str(s.session_id),
        'connection_id': str(s.connection.connection_id),
        'connection_name': s.connection.name,
        'claude_session_id': s.claude_session_id,
        'status': s.status,
        'working_dir': s.working_dir,
        'initial_prompt': s.initial_prompt,
        'permission_mode': s.permission_mode,
        'priority': s.priority,
        'webhook_url': s.webhook_url,
        'model_info': s.model_info,
        'result_text': s.result_text,
        'input_tokens': s.input_tokens,
        'output_tokens': s.output_tokens,
        'cost_usd': s.cost_usd,
        'duration_seconds': s.duration_seconds,
        'created_at': s.created_at.isoformat(),
        'started_at': s.started_at.isoformat() if s.started_at else None,
        'ended_at': s.ended_at.isoformat() if s.ended_at else None,
    }
    if include_messages:
        msgs = list(BridgeMessage.objects.filter(session=s).values(
            'id', 'direction', 'msg_type', 'content', 'seq', 'timestamp'
        ))
        for m in msgs:
            m['timestamp'] = m['timestamp'].isoformat()
        d['messages'] = msgs
        perms = list(PendingPermission.objects.filter(session=s).values(
            'permission_id', 'tool_name', 'tool_input', 'status', 'created_at', 'responded_at'
        ))
        for p in perms:
            p['permission_id'] = str(p['permission_id'])
            p['created_at'] = p['created_at'].isoformat()
            p['responded_at'] = p['responded_at'].isoformat() if p['responded_at'] else None
        d['permissions'] = perms
    return d


# ─────────────────────────────────────────────────────────────
# Bridge Client Endpoints  (called by claude_bridge_client.py)
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class BridgeConnectView(View):
    def post(self, request):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)

        data = json.loads(request.body or b'{}')
        cid = data.get('connection_id')
        conn = None
        if cid:
            try:
                conn = BridgeConnection.objects.get(connection_id=cid, user=user)
            except BridgeConnection.DoesNotExist:
                pass

        if not conn:
            conn = BridgeConnection.objects.create(
                user=user,
                name=data.get('name', 'My Computer'),
                os_info=data.get('os_info', ''),
                bridge_version=data.get('version', '2.0'),
            )

        conn.status = 'online'
        conn.last_heartbeat = timezone.now()
        conn.name = data.get('name', conn.name)
        conn.os_info = data.get('os_info', conn.os_info)
        conn.bridge_version = data.get('version', conn.bridge_version)
        conn.save()

        return JsonResponse({
            'connection_id': str(conn.connection_id),
            'name': conn.name,
            'default_priority': conn.default_priority,
            'default_permission_mode': conn.default_permission_mode,
        })


@method_decorator(csrf_exempt, name='dispatch')
class BridgeHeartbeatView(View):
    def post(self, request, connection_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=user)
        except BridgeConnection.DoesNotExist:
            return JsonResponse({'error': '未找到'}, status=404)
        conn.status = 'online'
        conn.last_heartbeat = timezone.now()
        conn.save(update_fields=['status', 'last_heartbeat'])
        return JsonResponse({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class BridgePollView(View):
    """Legacy poll endpoint — kept for backward compat with v1 clients."""
    def get(self, request, connection_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=user)
        except BridgeConnection.DoesNotExist:
            return JsonResponse({'error': '未找到'}, status=404)

        conn.status = 'online'
        conn.last_heartbeat = timezone.now()
        conn.save(update_fields=['status', 'last_heartbeat'])

        cmds = PendingCommand.objects.filter(connection=conn, status='pending').select_related('session')[:5]
        result = []
        for cmd in cmds:
            result.append({
                'cmd_id': cmd.id,
                'cmd_type': cmd.cmd_type,
                'session_id': str(cmd.session.session_id) if cmd.session else None,
                'data': cmd.data,
            })
            cmd.status = 'delivered'
            cmd.delivered_at = timezone.now()
            cmd.save(update_fields=['status', 'delivered_at'])

        return JsonResponse({'commands': result})


@method_decorator(csrf_exempt, name='dispatch')
class BridgePriorityQueueView(View):
    """v2 queue: returns tasks sorted by priority + urgent send/cancel commands."""
    def get(self, request, connection_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=user)
        except BridgeConnection.DoesNotExist:
            return JsonResponse({'error': '未找到'}, status=404)

        conn.status = 'online'
        conn.last_heartbeat = timezone.now()
        conn.save(update_fields=['status', 'last_heartbeat'])

        result = []

        # 1. Urgent commands: cancel_session and send_message have immediate priority
        urgent = PendingCommand.objects.filter(
            connection=conn, status='pending',
            cmd_type__in=['cancel_session', 'send_message']
        ).select_related('session')[:5]
        for cmd in urgent:
            result.append({
                'cmd_id': cmd.id,
                'cmd_type': cmd.cmd_type,
                'session_id': str(cmd.session.session_id) if cmd.session else None,
                'data': cmd.data,
            })
            cmd.status = 'delivered'
            cmd.delivered_at = timezone.now()
            cmd.save(update_fields=['status', 'delivered_at'])

        # 2. Queued tasks by priority (highest first), up to 3 concurrent
        if len(result) < 3:
            queued = BridgeSession.objects.filter(
                connection=conn, status='queued'
            ).order_by('-priority', 'created_at')[:3 - len(result)]

            for task in queued:
                result.append({
                    'cmd_id': None,
                    'cmd_type': 'start_session',
                    'session_id': str(task.session_id),
                    'data': {
                        'session_id': str(task.session_id),
                        'working_dir': task.working_dir,
                        'prompt': task.initial_prompt,
                        'permission_mode': task.permission_mode,
                        'priority': task.priority,
                    },
                })
                # Mark as being dispatched
                task.status = 'pending'
                task.save(update_fields=['status'])

        return JsonResponse({'commands': result})


@method_decorator(csrf_exempt, name='dispatch')
class BridgePostMessageView(View):
    """Bridge client posts a Claude event to the platform."""
    def post(self, request, session_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.select_related('connection__user').get(session_id=session_id)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)
        if session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        data = json.loads(request.body or b'{}')
        msg = BridgeMessage.objects.create(
            session=session,
            direction=data.get('direction', 'from_claude'),
            msg_type=data.get('type', 'text'),
            content=data.get('content', {}),
            seq=_next_seq(session),
        )

        if 'claude_session_id' in data:
            session.claude_session_id = data['claude_session_id']
            session.save(update_fields=['claude_session_id'])

        return JsonResponse({'id': msg.id, 'seq': msg.seq})


@method_decorator(csrf_exempt, name='dispatch')
class BridgeUpdateSessionView(View):
    """Bridge client updates session status / model info / stats."""
    def post(self, request, session_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.select_related('connection__user').get(session_id=session_id)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)
        if session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        data = json.loads(request.body or b'{}')
        new_status = data.get('status')

        if new_status:
            # Set started_at on first run
            if new_status == 'running' and not session.started_at:
                session.started_at = timezone.now()
            session.status = new_status

        if 'model_info' in data:
            session.model_info = data['model_info']
            # Extract stats from model_info
            mi = data['model_info']
            if 'total_cost_usd' in mi:
                session.cost_usd = mi['total_cost_usd'] or 0
            if 'total_input_tokens' in mi:
                session.input_tokens = mi['total_input_tokens'] or 0
            if 'total_output_tokens' in mi:
                session.output_tokens = mi['total_output_tokens'] or 0

        if 'result_text' in data:
            session.result_text = data['result_text']

        if 'claude_session_id' in data:
            session.claude_session_id = data['claude_session_id']

        is_terminal = session.status in TERMINAL_STATUSES
        if is_terminal and not session.ended_at:
            session.ended_at = timezone.now()
            if session.started_at:
                session.duration_seconds = (session.ended_at - session.started_at).total_seconds()

        session.save()

        # Fire webhook if set and not yet sent
        if is_terminal and session.webhook_url and not session.webhook_sent:
            payload = {
                'event': 'task_completed',
                'task_id': str(session.session_id),
                'status': session.status,
                'working_dir': session.working_dir,
                'prompt': session.initial_prompt[:200],
                'cost_usd': session.cost_usd,
                'input_tokens': session.input_tokens,
                'output_tokens': session.output_tokens,
                'duration_seconds': session.duration_seconds,
                'result_text': session.result_text[:500],
            }
            t = threading.Thread(target=_fire_webhook, args=(session.webhook_url, payload), daemon=True)
            t.start()
            session.webhook_sent = True
            session.save(update_fields=['webhook_sent'])

        return JsonResponse({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class BridgeCreatePermissionView(View):
    """Bridge creates a permission request."""
    def post(self, request, session_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.select_related('connection__user').get(session_id=session_id)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)
        if session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        data = json.loads(request.body or b'{}')
        perm = PendingPermission.objects.create(
            session=session,
            tool_name=data.get('tool_name', ''),
            tool_input=data.get('tool_input', {}),
            tool_use_id=data.get('tool_use_id', ''),
        )

        BridgeMessage.objects.create(
            session=session,
            direction='system',
            msg_type='permission_request',
            content={
                'permission_id': str(perm.permission_id),
                'tool_name': perm.tool_name,
                'tool_input': perm.tool_input,
                'tool_use_id': perm.tool_use_id,
            },
            seq=_next_seq(session),
        )
        session.status = 'waiting'
        session.save(update_fields=['status'])

        return JsonResponse({'permission_id': str(perm.permission_id)})


@method_decorator(csrf_exempt, name='dispatch')
class BridgePollPermissionView(View):
    """Bridge polls for a permission response."""
    def get(self, request, permission_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            perm = PendingPermission.objects.select_related('session__connection__user').get(permission_id=permission_id)
        except PendingPermission.DoesNotExist:
            return JsonResponse({'error': '未找到'}, status=404)
        if perm.session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        if perm.status == 'pending':
            elapsed = (timezone.now() - perm.created_at).total_seconds()
            if elapsed > 90:
                perm.status = 'timeout'
                perm.save(update_fields=['status'])

        return JsonResponse({'permission_id': str(perm.permission_id), 'status': perm.status})


# ─────────────────────────────────────────────────────────────
# Browser Endpoints
# ─────────────────────────────────────────────────────────────

class BridgeConnectionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        threshold = timezone.now() - timezone.timedelta(seconds=30)
        BridgeConnection.objects.filter(
            user=request.user, status='online', last_heartbeat__lt=threshold
        ).update(status='offline')

        conns = BridgeConnection.objects.filter(user=request.user)
        return Response([{
            'id': str(c.connection_id),
            'name': c.name,
            'status': c.status,
            'os_info': c.os_info,
            'last_heartbeat': c.last_heartbeat.isoformat() if c.last_heartbeat else None,
            'session_count': c.sessions.count(),
            'default_webhook_url': c.default_webhook_url,
            'default_permission_mode': c.default_permission_mode,
            'default_priority': c.default_priority,
            'created_at': c.created_at.isoformat(),
        } for c in conns])


class BridgeConnectionConfigView(APIView):
    """PATCH to update per-connection task defaults."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, connection_id):
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=request.user)
        except BridgeConnection.DoesNotExist:
            return Response({'error': '连接未找到'}, status=404)

        data = request.data
        if 'default_webhook_url' in data:
            conn.default_webhook_url = data['default_webhook_url']
        if 'default_permission_mode' in data:
            if data['default_permission_mode'] in ('default', 'full_auto', 'read_only'):
                conn.default_permission_mode = data['default_permission_mode']
        if 'default_priority' in data:
            p = int(data['default_priority'])
            if 1 <= p <= 10:
                conn.default_priority = p
        if 'name' in data:
            conn.name = data['name'][:200]
        conn.save()
        return Response({'ok': True})


class BridgeTaskCreateView(APIView):
    """Create a new task in the priority queue."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        conn_id = data.get('connection_id')
        if not conn_id:
            return Response({'error': '缺少 connection_id'}, status=400)
        try:
            conn = BridgeConnection.objects.get(connection_id=conn_id, user=request.user)
        except BridgeConnection.DoesNotExist:
            return Response({'error': '连接未找到'}, status=404)
        if conn.status != 'online':
            return Response({'error': '桥接客户端当前离线，请先启动 claude_bridge_client.py'}, status=400)

        prompt = data.get('prompt', '').strip()
        if not prompt:
            return Response({'error': '任务描述不能为空'}, status=400)

        priority = int(data.get('priority', conn.default_priority))
        priority = max(1, min(10, priority))

        session = BridgeSession.objects.create(
            connection=conn,
            working_dir=data.get('working_dir', '~'),
            initial_prompt=prompt,
            permission_mode=data.get('permission_mode', conn.default_permission_mode),
            priority=priority,
            webhook_url=data.get('webhook_url', conn.default_webhook_url),
            status='queued',
        )
        return Response({
            'session_id': str(session.session_id),
            'status': session.status,
            'priority': session.priority,
        }, status=201)


class BridgeAllSessionsView(APIView):
    """List all tasks for the current user (across all connections)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = BridgeSession.objects.filter(
            connection__user=request.user
        ).select_related('connection')[:100]
        return Response([{
            'id': str(s.session_id),
            'connection_id': str(s.connection.connection_id),
            'connection_name': s.connection.name,
            'status': s.status,
            'working_dir': s.working_dir,
            'initial_prompt': s.initial_prompt[:120],
            'permission_mode': s.permission_mode,
            'priority': s.priority,
            'cost_usd': s.cost_usd,
            'input_tokens': s.input_tokens,
            'output_tokens': s.output_tokens,
            'model_info': s.model_info,
            'created_at': s.created_at.isoformat(),
            'started_at': s.started_at.isoformat() if s.started_at else None,
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
            'duration_seconds': s.duration_seconds,
        } for s in sessions])


# Keep old per-connection session list + create for compat
class BridgeSessionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, connection_id):
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=request.user)
        except BridgeConnection.DoesNotExist:
            return Response({'error': '连接未找到'}, status=404)
        sessions = conn.sessions.all()
        return Response([{
            'id': str(s.session_id),
            'status': s.status,
            'working_dir': s.working_dir,
            'initial_prompt': s.initial_prompt[:120],
            'permission_mode': s.permission_mode,
            'priority': s.priority,
            'cost_usd': s.cost_usd,
            'model_info': s.model_info,
            'created_at': s.created_at.isoformat(),
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
        } for s in sessions])

    def post(self, request, connection_id):
        try:
            conn = BridgeConnection.objects.get(connection_id=connection_id, user=request.user)
        except BridgeConnection.DoesNotExist:
            return Response({'error': '连接未找到'}, status=404)
        if conn.status != 'online':
            return Response({'error': '桥接客户端当前离线'}, status=400)

        data = request.data
        priority = max(1, min(10, int(data.get('priority', conn.default_priority))))
        session = BridgeSession.objects.create(
            connection=conn,
            working_dir=data.get('working_dir', '~'),
            initial_prompt=data.get('prompt', ''),
            permission_mode=data.get('permission_mode', 'default'),
            priority=priority,
            webhook_url=data.get('webhook_url', conn.default_webhook_url),
            status='queued',
        )
        return Response({'session_id': str(session.session_id), 'status': session.status}, status=201)


class BridgeSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = BridgeSession.objects.select_related('connection').get(
                session_id=session_id, connection__user=request.user
            )
        except BridgeSession.DoesNotExist:
            return Response({'error': '任务未找到'}, status=404)
        return Response(_session_to_dict(session, include_messages=True))

    def delete(self, request, session_id):
        try:
            session = BridgeSession.objects.get(session_id=session_id, connection__user=request.user)
        except BridgeSession.DoesNotExist:
            return Response({'error': '任务未找到'}, status=404)

        if session.status in ('queued', 'pending', 'running', 'waiting'):
            if session.status not in ('queued', 'pending'):
                PendingCommand.objects.create(
                    connection=session.connection,
                    session=session,
                    cmd_type='cancel_session',
                    data={'session_id': str(session.session_id)},
                )
            session.status = 'cancelled'
            session.ended_at = timezone.now()
            session.save()
        return Response({'cancelled': True})


class BridgeSendMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, session_id):
        try:
            session = BridgeSession.objects.get(session_id=session_id, connection__user=request.user)
        except BridgeSession.DoesNotExist:
            return Response({'error': '任务未找到'}, status=404)

        message = request.data.get('message', '').strip()
        if not message:
            return Response({'error': '消息不能为空'}, status=400)

        BridgeMessage.objects.create(
            session=session,
            direction='from_user',
            msg_type='user_input',
            content={'text': message},
            seq=_next_seq(session),
        )
        PendingCommand.objects.create(
            connection=session.connection,
            session=session,
            cmd_type='send_message',
            data={'session_id': str(session.session_id), 'message': message},
        )
        return Response({'ok': True})


class BridgeRespondPermissionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, permission_id):
        try:
            perm = PendingPermission.objects.select_related('session__connection__user').get(permission_id=permission_id)
        except PendingPermission.DoesNotExist:
            return Response({'error': '权限请求未找到'}, status=404)
        if perm.session.connection.user != request.user:
            return Response({'error': '无权操作'}, status=403)

        decision = request.data.get('decision')
        if decision not in ('approved', 'denied'):
            return Response({'error': "decision must be 'approved' or 'denied'"}, status=400)

        perm.status = decision
        perm.responded_at = timezone.now()
        perm.save()

        session = perm.session
        BridgeMessage.objects.create(
            session=session,
            direction='from_user',
            msg_type='permission_response',
            content={
                'permission_id': str(perm.permission_id),
                'tool_name': perm.tool_name,
                'decision': decision,
            },
            seq=_next_seq(session),
        )
        if decision == 'approved':
            session.status = 'running'
            session.save(update_fields=['status'])

        return Response({'ok': True, 'decision': decision})


# ─────────────────────────────────────────────────────────────
# SSE Stream
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class BridgeSessionStreamView(View):
    def get(self, request, session_id):
        user = token_auth_user(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.get(session_id=session_id, connection__user=user)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '任务未找到'}, status=404)

        def generate():
            last_seq = int(request.GET.get('since', -1))
            max_cycles = 720  # ~6 min

            session.refresh_from_db()
            yield f"data: {json.dumps({'type': 'session_info', 'status': session.status, 'model_info': session.model_info, 'cost_usd': session.cost_usd, 'priority': session.priority})}\n\n"

            existing = BridgeMessage.objects.filter(session=session, seq__gt=last_seq).order_by('seq')
            for msg in existing:
                yield f"data: {json.dumps({'type': 'message', 'id': msg.id, 'direction': msg.direction, 'msg_type': msg.msg_type, 'content': msg.content, 'seq': msg.seq})}\n\n"
                last_seq = msg.seq

            if session.status in TERMINAL_STATUSES:
                yield f"data: {json.dumps({'type': 'done', 'status': session.status})}\n\n"
                return

            for _ in range(max_cycles):
                time.sleep(0.5)
                new_msgs = BridgeMessage.objects.filter(session=session, seq__gt=last_seq).order_by('seq')
                for msg in new_msgs:
                    yield f"data: {json.dumps({'type': 'message', 'id': msg.id, 'direction': msg.direction, 'msg_type': msg.msg_type, 'content': msg.content, 'seq': msg.seq})}\n\n"
                    last_seq = msg.seq

                session.refresh_from_db(fields=['status', 'model_info', 'cost_usd'])
                yield f"data: {json.dumps({'type': 'status', 'status': session.status, 'model_info': session.model_info, 'cost_usd': session.cost_usd})}\n\n"

                if session.status in TERMINAL_STATUSES:
                    yield f"data: {json.dumps({'type': 'done', 'status': session.status})}\n\n"
                    break

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


# ─────────────────────────────────────────────────────────────
# Stats
# ─────────────────────────────────────────────────────────────

class BridgeStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = BridgeSession.objects.filter(connection__user=request.user)

        agg = sessions.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status__in=['queued', 'pending', 'running', 'waiting'])),
            completed=Count('id', filter=Q(status='completed')),
            failed=Count('id', filter=Q(status='error')),
            cancelled=Count('id', filter=Q(status='cancelled')),
            total_cost=Sum('cost_usd'),
            total_input=Sum('input_tokens'),
            total_output=Sum('output_tokens'),
        )
        # None → 0
        for k in ('total_cost', 'total_input', 'total_output'):
            if agg[k] is None:
                agg[k] = 0

        per_conn = []
        for conn in BridgeConnection.objects.filter(user=request.user):
            cs = sessions.filter(connection=conn)
            ca = cs.aggregate(
                total=Count('id'),
                completed=Count('id', filter=Q(status='completed')),
                failed=Count('id', filter=Q(status='error')),
                total_cost=Sum('cost_usd'),
                total_input=Sum('input_tokens'),
                total_output=Sum('output_tokens'),
            )
            for k in ('total_cost', 'total_input', 'total_output'):
                if ca[k] is None:
                    ca[k] = 0
            per_conn.append({
                'connection_id': str(conn.connection_id),
                'name': conn.name,
                'status': conn.status,
                **ca,
            })

        # Recent completed tasks
        recent = sessions.filter(status='completed').order_by('-ended_at')[:5]
        recent_list = [{
            'id': str(s.session_id),
            'prompt': s.initial_prompt[:80],
            'cost_usd': s.cost_usd,
            'duration_seconds': s.duration_seconds,
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
        } for s in recent]

        return Response({
            'overall': agg,
            'per_connection': per_conn,
            'recent_completed': recent_list,
        })


# ─────────────────────────────────────────────────────────────
# Script Download & Installer
# ─────────────────────────────────────────────────────────────

class BridgeScriptDownloadView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        import os
        try:
            from rest_framework.authtoken.models import Token
            token_key = Token.objects.get(user=request.user).key
        except Exception:
            token_key = 'YOUR_TOKEN_HERE'

        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'claude_bridge_client.py')
        try:
            with open(script_path) as f:
                script = f.read()
        except FileNotFoundError:
            return Response({'error': '脚本文件未找到'}, status=500)

        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/').rstrip('/'))
        script = script.replace('__PLATFORM_URL__', site_url)
        script = script.replace('__USER_TOKEN__', token_key)

        resp = HttpResponse(script, content_type='text/x-python; charset=utf-8')
        resp['Content-Disposition'] = 'attachment; filename="claude_bridge_client.py"'
        return resp


class BridgeInstallerView(View):
    def get(self, request):
        token = (request.GET.get('token') or '').strip()
        if not token:
            return HttpResponse('Missing token query parameter: ?token=YOUR_TOKEN', status=400, content_type='text/plain; charset=utf-8')

        from django.conf import settings
        site_url = getattr(settings, 'SITE_URL', request.build_absolute_uri('/').rstrip('/')).rstrip('/')
        script_url = f"{site_url}/api/bridge/client/script/"

        install_script = f"""#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required but not found in PATH."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required but not found in PATH."
  exit 1
fi

echo ">>> Downloading claude_bridge_client.py ..."
curl -fsSL -H "Authorization: Token {token}" "{script_url}" -o claude_bridge_client.py
chmod +x claude_bridge_client.py

echo ">>> Installing dependencies ..."
pip3 install requests --quiet

echo ">>> Done. Start the bridge with:"
echo "    python3 claude_bridge_client.py"
"""
        return HttpResponse(install_script, content_type='text/plain; charset=utf-8')
