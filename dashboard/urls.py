from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),

    # 用户管理
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle/', views.user_toggle_active, name='user_toggle'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    # 系统配置
    path('config/', views.site_config, name='site_config'),

    # 验证码记录
    path('codes/', views.verification_codes, name='verification_codes'),
    path('codes/<int:pk>/delete/', views.code_delete, name='code_delete'),

    # 写作项目
    path('projects/', views.project_list, name='project_list'),
    path('projects/<int:pk>/delete/', views.project_delete, name='project_delete'),

    # 共享小说
    path('novels/', views.novel_list, name='novel_list'),
    path('novels/<int:pk>/toggle/', views.novel_toggle_status, name='novel_toggle'),
    path('novels/<int:pk>/delete/', views.novel_delete, name='novel_delete'),

    # 评论管理
    path('comments/', views.comment_list, name='comment_list'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment_delete'),

    # Hub 应用管理
    path('apps/', views.app_list, name='app_list'),
    path('apps/create/', views.app_create, name='app_create'),
    path('apps/<int:pk>/edit/', views.app_edit, name='app_edit'),
    path('apps/<int:pk>/delete/', views.app_delete, name='app_delete'),

    # OCR 项目
    path('ocr/', views.ocr_list, name='ocr_list'),
    path('ocr/<str:pk>/delete/', views.ocr_delete, name='ocr_delete'),
]
