import uuid
from django.db import models
from accounts.models import User


class BridgeConnection(models.Model):
    """A user's local Claude Code bridge daemon."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bridge_connections')
    connection_id = models.UUIDField(default=uuid.uuid4, unique=True)
    name = models.CharField(max_length=200, default='My Computer')
    status = models.CharField(max_length=20, default='offline')  # online, offline
    last_heartbeat = models.DateTimeField(null=True, blank=True)
    os_info = models.CharField(max_length=200, blank=True)
    bridge_version = models.CharField(max_length=50, default='1.0')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-last_heartbeat']

    def __str__(self):
        return f"{self.user.username} — {self.name} ({self.status})"


class BridgeSession(models.Model):
    """A Claude Code session running locally via the bridge."""
    PERMISSION_CHOICES = [
        ('full_auto', 'Full Auto (dangerously-skip-permissions)'),
        ('read_only', 'Read Only'),
        ('default', 'Default (Claude Code standard)'),
    ]

    connection = models.ForeignKey(BridgeConnection, on_delete=models.CASCADE, related_name='sessions')
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    claude_session_id = models.CharField(max_length=200, blank=True)
    working_dir = models.CharField(max_length=1000)
    initial_prompt = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    # pending | running | waiting | completed | error | cancelled
    permission_mode = models.CharField(max_length=20, default='default', choices=PERMISSION_CHOICES)
    model_info = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.session_id} [{self.status}]"


class BridgeMessage(models.Model):
    """A single event/message in a bridge session."""
    session = models.ForeignKey(BridgeSession, on_delete=models.CASCADE, related_name='messages')
    direction = models.CharField(max_length=20)  # from_claude | from_user | system
    msg_type = models.CharField(max_length=30)
    # system_init | text | tool_use | tool_result | permission_request
    # permission_response | user_input | result | error | status_update
    content = models.JSONField()
    seq = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['seq', 'timestamp']


class PendingPermission(models.Model):
    """A permission request waiting for the user to approve/deny."""
    session = models.ForeignKey(BridgeSession, on_delete=models.CASCADE, related_name='permissions')
    permission_id = models.UUIDField(default=uuid.uuid4, unique=True)
    tool_name = models.CharField(max_length=100)
    tool_input = models.JSONField()
    tool_use_id = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, default='pending')  # pending | approved | denied | timeout
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']


class PendingCommand(models.Model):
    """A command queued for the bridge client to pick up via polling."""
    connection = models.ForeignKey(BridgeConnection, on_delete=models.CASCADE, related_name='pending_commands')
    session = models.ForeignKey(BridgeSession, on_delete=models.SET_NULL, null=True, blank=True, related_name='commands')
    cmd_type = models.CharField(max_length=30)  # start_session | send_message | cancel_session
    data = models.JSONField()
    status = models.CharField(max_length=20, default='pending')  # pending | delivered
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
