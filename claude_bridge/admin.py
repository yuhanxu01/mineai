from django.contrib import admin
from .models import BridgeConnection, BridgeSession, BridgeMessage, PendingPermission, PendingCommand


@admin.register(BridgeConnection)
class BridgeConnectionAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'status', 'last_heartbeat', 'bridge_version', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'name']


@admin.register(BridgeSession)
class BridgeSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'connection', 'status', 'permission_mode', 'working_dir', 'created_at']
    list_filter = ['status', 'permission_mode']


@admin.register(BridgeMessage)
class BridgeMessageAdmin(admin.ModelAdmin):
    list_display = ['session', 'direction', 'msg_type', 'seq', 'timestamp']
    list_filter = ['direction', 'msg_type']


@admin.register(PendingPermission)
class PendingPermissionAdmin(admin.ModelAdmin):
    list_display = ['session', 'tool_name', 'status', 'created_at', 'responded_at']
    list_filter = ['status']


@admin.register(PendingCommand)
class PendingCommandAdmin(admin.ModelAdmin):
    list_display = ['connection', 'cmd_type', 'status', 'created_at', 'delivered_at']
    list_filter = ['status', 'cmd_type']
