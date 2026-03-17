from django.urls import path
from . import views

urlpatterns = [
    # OCR
    path('ocr/', views.OCRView.as_view(), name='qbank-ocr'),

    # 我的题目 CRUD
    path('questions/', views.QuestionListView.as_view(), name='qbank-question-list'),
    path('questions/<int:pk>/', views.QuestionDetailView.as_view(), name='qbank-question-detail'),

    # AI 对话（SSE 流式）
    path('questions/<int:pk>/chat-stream/', views.chat_stream_view, name='qbank-chat-stream'),

    # 最终答案
    path('questions/<int:pk>/final/', views.FinalAnswerView.as_view(), name='qbank-final'),

    # 标准答案
    path('questions/<int:pk>/standard/', views.StandardAnswerView.as_view(), name='qbank-standard'),

    # 发布 / 取消发布
    path('questions/<int:pk>/publish/', views.PublishView.as_view(), name='qbank-publish'),

    # 共享题库
    path('shared/', views.SharedListView.as_view(), name='qbank-shared-list'),
    path('shared/<int:pk>/', views.SharedDetailView.as_view(), name='qbank-shared-detail'),
    path('shared/<int:pk>/comment/', views.CommentView.as_view(), name='qbank-comment'),
    path('shared/<int:pk>/like/', views.LikeView.as_view(), name='qbank-like'),
    path('shared/<int:pk>/favorite/', views.FavoriteView.as_view(), name='qbank-favorite'),
]
