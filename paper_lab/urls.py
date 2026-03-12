from django.urls import path
from . import views

urlpatterns = [
    # 研究项目
    path('projects/', views.ProjectListView.as_view()),
    path('projects/<int:pk>/', views.ProjectDetailView.as_view()),

    # 文献管理
    path('projects/<int:project_id>/literatures/', views.LiteratureListView.as_view()),
    path('projects/<int:project_id>/literatures/import-ocr/', views.LiteratureImportOCRView.as_view()),
    path('literatures/<int:lit_id>/', views.LiteratureDetailView.as_view()),
    path('literatures/<int:lit_id>/content/', views.LiteratureContentView.as_view()),
    path('literatures/<int:lit_id>/chunks/', views.LiteratureChunksView.as_view()),
    path('literatures/<int:lit_id>/reindex/', views.LiteratureReindexView.as_view()),
    path('literatures/<int:lit_id>/analysis/', views.LiteratureAnalysisView.as_view()),

    # 知识检索
    path('projects/<int:project_id>/search/', views.SearchView.as_view()),
    path('projects/<int:project_id>/explore/', views.ExploreView.as_view()),

    # 研究对话
    path('projects/<int:project_id>/conversations/', views.ConversationListView.as_view()),
    path('conversations/<int:conv_id>/', views.ConversationDetailView.as_view()),
    path('conversations/<int:conv_id>/chat/', views.ConversationChatStreamView.as_view()),

    # 研究笔记
    path('projects/<int:project_id>/notes/', views.NoteListView.as_view()),
    path('notes/<int:note_id>/', views.NoteDetailView.as_view()),

    # 研究灵感
    path('projects/<int:project_id>/ideas/', views.IdeaListView.as_view()),
    path('projects/<int:project_id>/ideas/generate/', views.IdeaGenerateView.as_view()),
    path('ideas/<int:idea_id>/', views.IdeaDetailView.as_view()),

    # 写作草稿
    path('projects/<int:project_id>/drafts/', views.DraftListView.as_view()),
    path('drafts/<int:draft_id>/', views.DraftDetailView.as_view()),
    path('drafts/<int:draft_id>/assist/', views.DraftWritingAssistView.as_view()),

    # 工具
    path('ocr-projects/', views.OCRProjectsForImportView.as_view()),
    path('token-stats/', views.TokenStatsView.as_view()),
]
