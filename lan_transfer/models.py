import datetime
import secrets
import string

from django.db import models
from django.utils import timezone


class TransferRoom(models.Model):
    code = models.CharField(max_length=8, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    @staticmethod
    def generate_code(length=6):
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    @classmethod
    def create_room(cls, ttl_minutes=30):
        expires_at = timezone.now() + datetime.timedelta(minutes=ttl_minutes)
        while True:
            code = cls.generate_code()
            if not cls.objects.filter(code=code).exists():
                return cls.objects.create(code=code, expires_at=expires_at)


class RoomPeer(models.Model):
    room = models.ForeignKey(TransferRoom, on_delete=models.CASCADE, related_name='peers')
    peer_id = models.CharField(max_length=48, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)


class SignalMessage(models.Model):
    KIND_OFFER = 'offer'
    KIND_ANSWER = 'answer'
    KIND_CANDIDATE = 'candidate'

    KINDS = [
        (KIND_OFFER, 'offer'),
        (KIND_ANSWER, 'answer'),
        (KIND_CANDIDATE, 'candidate'),
    ]

    room = models.ForeignKey(TransferRoom, on_delete=models.CASCADE, related_name='messages')
    sender_peer_id = models.CharField(max_length=48, db_index=True)
    target_peer_id = models.CharField(max_length=48, null=True, blank=True, db_index=True)
    kind = models.CharField(max_length=16, choices=KINDS)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['room', 'id']),
            models.Index(fields=['room', 'target_peer_id', 'id']),
        ]
