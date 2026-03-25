from django.urls import path
from . import views

urlpatterns = [
    # 文档项目管理
    path('documents/', views.DocumentProjectListView.as_view(), name='doc_documents'),
    path('documents/<str:doc_id>/', views.DocumentProjectDetailView.as_view(), name='doc_document_detail'),

    # 云盘文件
    path('cloud-files/', views.CloudFileListView.as_view(), name='doc_cloud_files'),

    # 页面缓存
    path('documents/<str:doc_id>/pages/upload/', views.PageUploadView.as_view(), name='doc_page_upload'),
    path('documents/<str:doc_id>/pages/<int:page_num>/', views.PageDetailView.as_view(), name='doc_page_detail'),

    # OCR解析
    path('documents/<str:doc_id>/pages/<int:page_num>/parse/', views.PageParseView.as_view(), name='doc_page_parse'),
    path('documents/<str:doc_id>/parse/batch/', views.BatchParseView.as_view(), name='doc_batch_parse'),

    # 缓存配额
    path('cache/quota/', views.CacheQuotaView.as_view(), name='doc_cache_quota'),

    # 对话管理
    path('documents/<str:doc_id>/chats/', views.ChatSessionListView.as_view(), name='doc_chats'),
    path('documents/<str:doc_id>/chats/<int:session_id>/', views.ChatSessionDetailView.as_view(), name='doc_chat_detail'),
    path('documents/<str:doc_id>/chats/<int:session_id>/stream/', views.ChatStreamView.as_view(), name='doc_chat_stream'),
]
