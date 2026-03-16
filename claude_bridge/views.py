import json
import time

from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import BridgeConnection, BridgeSession, BridgeMessage, PendingPermission, PendingCommand


def _token_auth(request):
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


# ─────────────────────────────────────────────────────────────
# Bridge Client Endpoints  (called by the local Python script)
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class BridgeConnectView(View):
    def post(self, request):
        user = _token_auth(request)
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
                bridge_version=data.get('version', '1.0'),
            )

        conn.status = 'online'
        conn.last_heartbeat = timezone.now()
        conn.name = data.get('name', conn.name)
        conn.os_info = data.get('os_info', conn.os_info)
        conn.save()

        return JsonResponse({'connection_id': str(conn.connection_id), 'name': conn.name})


@method_decorator(csrf_exempt, name='dispatch')
class BridgeHeartbeatView(View):
    def post(self, request, connection_id):
        user = _token_auth(request)
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
    """Bridge client polls for queued commands."""
    def get(self, request, connection_id):
        user = _token_auth(request)
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
class BridgePostMessageView(View):
    """Bridge client posts a Claude event to the platform."""
    def post(self, request, session_id):
        user = _token_auth(request)
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
    """Bridge client updates session status / model info."""
    def post(self, request, session_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.select_related('connection__user').get(session_id=session_id)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)
        if session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        data = json.loads(request.body or b'{}')
        if 'status' in data:
            session.status = data['status']
        if 'model_info' in data:
            session.model_info = data['model_info']
        if 'claude_session_id' in data:
            session.claude_session_id = data['claude_session_id']
        if session.status in ('completed', 'error', 'cancelled') and not session.ended_at:
            session.ended_at = timezone.now()
        session.save()
        return JsonResponse({'ok': True})


@method_decorator(csrf_exempt, name='dispatch')
class BridgeCreatePermissionView(View):
    """Bridge creates a permission request and posts it as a message."""
    def post(self, request, session_id):
        user = _token_auth(request)
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
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            perm = PendingPermission.objects.select_related('session__connection__user').get(permission_id=permission_id)
        except PendingPermission.DoesNotExist:
            return JsonResponse({'error': '未找到'}, status=404)
        if perm.session.connection.user != user:
            return JsonResponse({'error': '无权操作'}, status=403)

        # Auto-timeout after 90s
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
            'created_at': c.created_at.isoformat(),
        } for c in conns])


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
            return Response({'error': '桥接客户端当前离线，请先启动 claude_bridge.py'}, status=400)

        data = request.data
        session = BridgeSession.objects.create(
            connection=conn,
            working_dir=data.get('working_dir', '~'),
            initial_prompt=data.get('prompt', ''),
            permission_mode=data.get('permission_mode', 'default'),
        )
        PendingCommand.objects.create(
            connection=conn,
            session=session,
            cmd_type='start_session',
            data={
                'session_id': str(session.session_id),
                'working_dir': session.working_dir,
                'prompt': session.initial_prompt,
                'permission_mode': session.permission_mode,
            },
        )
        return Response({'session_id': str(session.session_id), 'status': session.status}, status=201)


class BridgeAllSessionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = BridgeSession.objects.filter(connection__user=request.user).select_related('connection')[:50]
        return Response([{
            'id': str(s.session_id),
            'connection_id': str(s.connection.connection_id),
            'connection_name': s.connection.name,
            'status': s.status,
            'working_dir': s.working_dir,
            'initial_prompt': s.initial_prompt[:120],
            'permission_mode': s.permission_mode,
            'model_info': s.model_info,
            'created_at': s.created_at.isoformat(),
            'ended_at': s.ended_at.isoformat() if s.ended_at else None,
        } for s in sessions])


class BridgeSessionDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = BridgeSession.objects.select_related('connection').get(
                session_id=session_id, connection__user=request.user
            )
        except BridgeSession.DoesNotExist:
            return Response({'error': '会话未找到'}, status=404)

        messages = list(BridgeMessage.objects.filter(session=session).values(
            'id', 'direction', 'msg_type', 'content', 'seq', 'timestamp'
        ))
        for m in messages:
            m['timestamp'] = m['timestamp'].isoformat()

        perms = list(PendingPermission.objects.filter(session=session).values(
            'permission_id', 'tool_name', 'tool_input', 'status', 'created_at', 'responded_at'
        ))
        for p in perms:
            p['permission_id'] = str(p['permission_id'])
            p['created_at'] = p['created_at'].isoformat()
            p['responded_at'] = p['responded_at'].isoformat() if p['responded_at'] else None

        return Response({
            'id': str(session.session_id),
            'claude_session_id': session.claude_session_id,
            'connection_id': str(session.connection.connection_id),
            'connection_name': session.connection.name,
            'status': session.status,
            'working_dir': session.working_dir,
            'initial_prompt': session.initial_prompt,
            'permission_mode': session.permission_mode,
            'model_info': session.model_info,
            'created_at': session.created_at.isoformat(),
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            'messages': messages,
            'permissions': perms,
        })

    def delete(self, request, session_id):
        try:
            session = BridgeSession.objects.get(session_id=session_id, connection__user=request.user)
        except BridgeSession.DoesNotExist:
            return Response({'error': '会话未找到'}, status=404)
        if session.status in ('pending', 'running', 'waiting'):
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
            return Response({'error': '会话未找到'}, status=404)

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
# SSE Stream (browser polls for live updates)
# ─────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name='dispatch')
class BridgeSessionStreamView(View):
    def get(self, request, session_id):
        user = _token_auth(request)
        if not user:
            return JsonResponse({'error': '需要认证'}, status=401)
        try:
            session = BridgeSession.objects.get(session_id=session_id, connection__user=user)
        except BridgeSession.DoesNotExist:
            return JsonResponse({'error': '会话未找到'}, status=404)

        def generate():
            last_seq = int(request.GET.get('since', -1))
            max_cycles = 720  # ~6 min at 0.5s intervals

            # Send current session state
            session.refresh_from_db()
            yield f"data: {json.dumps({'type': 'session_info', 'status': session.status, 'model_info': session.model_info})}\n\n"

            # Send messages since last_seq
            existing = BridgeMessage.objects.filter(session=session, seq__gt=last_seq).order_by('seq')
            for msg in existing:
                yield f"data: {json.dumps({'type': 'message', 'id': msg.id, 'direction': msg.direction, 'msg_type': msg.msg_type, 'content': msg.content, 'seq': msg.seq})}\n\n"
                last_seq = msg.seq

            if session.status in ('completed', 'error', 'cancelled'):
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return

            for _ in range(max_cycles):
                time.sleep(0.5)
                new_msgs = BridgeMessage.objects.filter(session=session, seq__gt=last_seq).order_by('seq')
                for msg in new_msgs:
                    yield f"data: {json.dumps({'type': 'message', 'id': msg.id, 'direction': msg.direction, 'msg_type': msg.msg_type, 'content': msg.content, 'seq': msg.seq})}\n\n"
                    last_seq = msg.seq

                session.refresh_from_db(fields=['status', 'model_info'])
                yield f"data: {json.dumps({'type': 'status', 'status': session.status, 'model_info': session.model_info})}\n\n"

                if session.status in ('completed', 'error', 'cancelled'):
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"
                    break

        resp = StreamingHttpResponse(generate(), content_type='text/event-stream')
        resp['Cache-Control'] = 'no-cache'
        resp['X-Accel-Buffering'] = 'no'
        return resp


# ─────────────────────────────────────────────────────────────
# Download Bridge Script
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
        resp['Content-Disposition'] = 'attachment; filename="claude_bridge.py"'
        return resp
