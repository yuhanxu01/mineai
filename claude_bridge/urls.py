from django.urls import path
from . import views

urlpatterns = [
    # ── Bridge client endpoints (called by claude_bridge_client.py) ──
    path('connect/', views.BridgeConnectView.as_view()),
    path('heartbeat/<uuid:connection_id>/', views.BridgeHeartbeatView.as_view()),
    path('poll/<uuid:connection_id>/', views.BridgePollView.as_view()),
    path('session/<uuid:session_id>/message/', views.BridgePostMessageView.as_view()),
    path('session/<uuid:session_id>/status/', views.BridgeUpdateSessionView.as_view()),
    path('session/<uuid:session_id>/permission/', views.BridgeCreatePermissionView.as_view()),
    path('permission/<uuid:permission_id>/poll/', views.BridgePollPermissionView.as_view()),

    # ── Browser endpoints ──
    path('connections/', views.BridgeConnectionListView.as_view()),
    path('connections/<uuid:connection_id>/sessions/', views.BridgeSessionListView.as_view()),
    path('sessions/', views.BridgeAllSessionsView.as_view()),
    path('sessions/<uuid:session_id>/', views.BridgeSessionDetailView.as_view()),
    path('sessions/<uuid:session_id>/stream/', views.BridgeSessionStreamView.as_view()),
    path('sessions/<uuid:session_id>/send/', views.BridgeSendMessageView.as_view()),
    path('permissions/<uuid:permission_id>/respond/', views.BridgeRespondPermissionView.as_view()),
    path('client/script/', views.BridgeScriptDownloadView.as_view()),
]
