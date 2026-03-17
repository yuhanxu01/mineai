from django.urls import path
from . import views

urlpatterns = [
    # Projects
    path('projects/', views.ProjectListView.as_view(), name='ca-project-list'),
    path('projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='ca-project-detail'),

    # Files
    path('projects/<int:project_id>/files/', views.FileListView.as_view(), name='ca-file-create'),
    path('projects/<int:project_id>/files/batch/', views.FileBatchUploadView.as_view(), name='ca-file-batch'),
    path('files/<int:file_id>/', views.FileDetailView.as_view(), name='ca-file-detail'),
    path('files/<int:file_id>/versions/', views.FileVersionListView.as_view(), name='ca-file-versions'),
    path('files/<int:file_id>/rollback/', views.FileRollbackView.as_view(), name='ca-file-rollback'),

    # Diffs
    path('files/<int:file_id>/apply_diffs/', views.ApplyDiffsView.as_view(), name='ca-apply-diffs'),

    # Sessions & Chat
    path('projects/<int:project_id>/sessions/', views.SessionListView.as_view(), name='ca-session-list'),
    path('sessions/<int:session_id>/', views.SessionDetailView.as_view(), name='ca-session-detail'),

    # Streaming (SSE)
    path('sessions/<int:session_id>/chat/', views.ChatStreamView.as_view(), name='ca-chat-stream'),
    path('files/<int:file_id>/suggest/', views.SuggestEditsStreamView.as_view(), name='ca-suggest-stream'),
    path('projects/<int:project_id>/generate/', views.GenerateCodeStreamView.as_view(), name='ca-generate-stream'),

    # Utilities
    path('files/<int:file_id>/explain/', views.ExplainCodeView.as_view(), name='ca-explain'),
    path('projects/<int:project_id>/analyze/', views.AnalyzeProjectView.as_view(), name='ca-analyze'),
    path('projects/<int:project_id>/memory/', views.MemoryStatsView.as_view(), name='ca-memory-stats'),

    # Upload limits config
    path('upload-limits/', views.UploadLimitsView.as_view(), name='ca-upload-limits'),

    # 本地模式：无状态 SSE 端点（不存储文件）
    path('local/suggest/', views.LocalSuggestView.as_view(), name='ca-local-suggest'),
    path('local/chat/',    views.LocalChatView.as_view(),    name='ca-local-chat'),
]
