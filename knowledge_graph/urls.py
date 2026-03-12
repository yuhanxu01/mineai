from django.urls import path
from . import views

urlpatterns = [
    # 图谱项目
    path('projects/', views.KGProjectListView.as_view()),
    path('projects/<int:kg_id>/', views.KGProjectDetailView.as_view()),

    # 图谱可视化数据
    path('projects/<int:kg_id>/graph/', views.KGGraphDataView.as_view()),

    # 节点管理
    path('projects/<int:kg_id>/nodes/', views.KGNodeListView.as_view()),
    path('projects/<int:kg_id>/nodes/<int:node_id>/', views.KGNodeDetailView.as_view()),

    # 边管理
    path('projects/<int:kg_id>/edges/', views.KGEdgeListView.as_view()),
    path('projects/<int:kg_id>/edges/<int:edge_id>/', views.KGEdgeDetailView.as_view()),

    # 检索与探索
    path('projects/<int:kg_id>/search/', views.KGSearchView.as_view()),
    path('projects/<int:kg_id>/subgraph/', views.KGSubgraphView.as_view()),
    path('projects/<int:kg_id>/path/', views.KGPathView.as_view()),

    # AI功能
    path('projects/<int:kg_id>/extract/', views.KGExtractView.as_view()),
    path('projects/<int:kg_id>/chat/', views.KGChatStreamView.as_view()),
    path('projects/<int:kg_id>/rank/', views.KGComputeRankView.as_view()),

    # 统计
    path('stats/', views.KGStatsView.as_view()),
]
