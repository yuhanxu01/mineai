from django.urls import path
from . import views

urlpatterns = [
    # 直连 API 模式
    path('recognize/', views.OCRRecognizeView.as_view(), name='ocr_recognize'),

    # 项目管理
    path('projects/', views.OCRProjectListView.as_view(), name='ocr_project_list'),
    path('projects/create/', views.OCRProjectCreateView.as_view(), name='ocr_project_create'),
    path('projects/<str:project_id>/', views.OCRProjectDetailView.as_view(), name='ocr_project_detail'),

    # 图片上传（Worker 中继 + API 模式）
    path('upload/', views.OCRUploadView.as_view(), name='ocr_upload'),

    # 页面详情（轮询状态用）
    path('pages/<int:page_id>/', views.OCRPageDetailView.as_view(), name='ocr_page_detail'),
    path('pages/<int:page_id>/feedback/', views.OCRFeedbackView.as_view(), name='ocr_page_feedback'),

    # Worker 回调（Redis 模式 Worker 处理完后调用）
    path('worker/callback/<str:token>/', views.OCRWorkerCallbackView.as_view(), name='ocr_worker_callback'),

    # 配额
    path('quota/', views.OCRQuotaView.as_view(), name='ocr_quota'),

    # 历史记录
    path('history/', views.OCRHistoryView.as_view(), name='ocr_history'),

    # 兼容旧 Worker 轮询协议
    path('get-empty-text-images/', views.OCREmptyTextView.as_view(), name='ocr_empty_text'),
    path('image/<int:page_id>/', views.OCRSubmitResultView.as_view(), name='ocr_submit_result'),
]
