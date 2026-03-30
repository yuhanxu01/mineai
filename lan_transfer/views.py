import secrets

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from .models import RoomPeer, SignalMessage, TransferRoom


class TransferPageView(TemplateView):
    template_name = 'lan_transfer/index.html'


def _cleanup_expired_rooms():
    TransferRoom.objects.filter(expires_at__lt=timezone.now()).delete()


def _json_error(message, status=400):
    return JsonResponse({'ok': False, 'error': message}, status=status)


def _new_peer_id():
    return secrets.token_urlsafe(18)


@csrf_exempt
@require_POST
def create_room(request):
    _cleanup_expired_rooms()

    room = TransferRoom.create_room(ttl_minutes=30)
    peer = RoomPeer.objects.create(room=room, peer_id=_new_peer_id())
    return JsonResponse(
        {
            'ok': True,
            'room_code': room.code,
            'peer_id': peer.peer_id,
            'expires_at': room.expires_at.isoformat(),
        }
    )


@csrf_exempt
@require_POST
def join_room(request):
    _cleanup_expired_rooms()

    room_code = (request.POST.get('room_code') or '').strip().upper()
    if not room_code:
        return _json_error('room_code 不能为空')

    room = TransferRoom.objects.filter(code=room_code).first()
    if not room:
        return _json_error('房间不存在或已过期', status=404)

    if room.peers.count() >= 2:
        return _json_error('该房间已满（仅支持 1 对 1 传输）', status=409)

    peer = RoomPeer.objects.create(room=room, peer_id=_new_peer_id())
    return JsonResponse(
        {
            'ok': True,
            'room_code': room.code,
            'peer_id': peer.peer_id,
            'expires_at': room.expires_at.isoformat(),
        }
    )


@csrf_exempt
@require_POST
def post_signal(request):
    room_code = (request.POST.get('room_code') or '').strip().upper()
    peer_id = (request.POST.get('peer_id') or '').strip()
    kind = (request.POST.get('kind') or '').strip()
    payload_text = request.POST.get('payload') or '{}'
    target_peer_id = (request.POST.get('target_peer_id') or '').strip() or None

    if kind not in {SignalMessage.KIND_OFFER, SignalMessage.KIND_ANSWER, SignalMessage.KIND_CANDIDATE}:
        return _json_error('非法信令类型')

    room = TransferRoom.objects.filter(code=room_code, expires_at__gt=timezone.now()).first()
    if not room:
        return _json_error('房间不存在或已过期', status=404)

    if not RoomPeer.objects.filter(room=room, peer_id=peer_id).exists():
        return _json_error('无效 peer_id', status=403)

    try:
        import json

        payload = json.loads(payload_text)
    except Exception:
        return _json_error('payload 必须是合法 JSON')

    msg = SignalMessage.objects.create(
        room=room,
        sender_peer_id=peer_id,
        target_peer_id=target_peer_id,
        kind=kind,
        payload=payload,
    )
    return JsonResponse({'ok': True, 'message_id': msg.id})


@require_GET
def poll_signals(request):
    room_code = (request.GET.get('room_code') or '').strip().upper()
    peer_id = (request.GET.get('peer_id') or '').strip()
    since_id = int(request.GET.get('since_id') or 0)

    room = TransferRoom.objects.filter(code=room_code, expires_at__gt=timezone.now()).first()
    if not room:
        return _json_error('房间不存在或已过期', status=404)

    if not RoomPeer.objects.filter(room=room, peer_id=peer_id).exists():
        return _json_error('无效 peer_id', status=403)

    queryset = (
        SignalMessage.objects.filter(room=room, id__gt=since_id)
        .exclude(sender_peer_id=peer_id)
        .order_by('id')[:200]
    )

    result = []
    max_id = since_id
    for msg in queryset:
        if msg.target_peer_id and msg.target_peer_id != peer_id:
            continue
        result.append(
            {
                'id': msg.id,
                'kind': msg.kind,
                'payload': msg.payload,
                'sender_peer_id': msg.sender_peer_id,
                'target_peer_id': msg.target_peer_id,
            }
        )
        max_id = max(max_id, msg.id)

    return JsonResponse({'ok': True, 'messages': result, 'since_id': max_id})


@require_GET
def room_info(request):
    room_code = (request.GET.get('room_code') or '').strip().upper()
    peer_id = (request.GET.get('peer_id') or '').strip()

    room = TransferRoom.objects.filter(code=room_code, expires_at__gt=timezone.now()).first()
    if not room:
        return _json_error('房间不存在或已过期', status=404)

    if not RoomPeer.objects.filter(room=room, peer_id=peer_id).exists():
        return _json_error('无效 peer_id', status=403)

    peers = list(room.peers.values_list('peer_id', flat=True))
    return JsonResponse(
        {
            'ok': True,
            'room_code': room.code,
            'peer_count': len(peers),
            'is_ready': len(peers) == 2,
            'expires_at': room.expires_at.isoformat(),
        }
    )
