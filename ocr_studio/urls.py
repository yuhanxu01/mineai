from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.UploadFileView.as_view(), name='ocr_upload'),
    path('upload-url/', views.UploadURLView.as_view(), name='ocr_upload_url'),
    path('projects/', views.ProjectsListView.as_view(), name='ocr_projects_list'),
    path('projects/<str:project_id>/', views.ProjectDetailView.as_view(), name='ocr_project_detail'),
    path('projects/<str:project_id>/pages/<int:page_num>/image/', views.PageImageView.as_view(), name='ocr_page_image'),
    path('projects/<str:project_id>/ocr/', views.SubmitOCRView.as_view(), name='ocr_submit'),
    path('projects/<str:project_id>/retry/<int:page_num>/', views.RetryPageView.as_view(), name='ocr_retry'),
    path('projects/<str:project_id>/status/', views.StatusView.as_view(), name='ocr_status'),
    path('projects/<str:project_id>/result/', views.ResultView.as_view(), name='ocr_result'),
    path('projects/<str:project_id>/result/download/', views.DownloadResultView.as_view(), name='ocr_download'),
    path('projects/<str:project_id>/page/<int:page_num>/result/', views.PageResultView.as_view(), name='ocr_page_result'),
    path('projects/<str:project_id>/delete/', views.DeleteProjectView.as_view(), name='ocr_delete'),
]
