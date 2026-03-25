from django.urls import path
from . import views

urlpatterns = [
    # 游戏管理
    path('game/', views.GameView.as_view(), name='banished-game'),
    path('game/new/', views.GameNewView.as_view(), name='banished-game-new'),
    path('game/sync/', views.GameSyncView.as_view(), name='banished-game-sync'),

    # 存档
    path('saves/', views.SaveListView.as_view(), name='banished-saves'),
    path('saves/<int:slot>/', views.SaveSlotView.as_view(), name='banished-save-slot'),
    path('saves/<int:slot>/load/', views.SaveLoadView.as_view(), name='banished-save-load'),

    # 交易市场
    path('market/', views.MarketView.as_view(), name='banished-market'),
    path('market/order/', views.MarketOrderView.as_view(), name='banished-market-order'),
    path('market/cancel/<int:order_id>/', views.MarketCancelView.as_view(), name='banished-market-cancel'),
    path('market/history/<str:resource>/', views.MarketHistoryView.as_view(), name='banished-market-history'),

    # 排行榜
    path('leaderboard/', views.LeaderboardView.as_view(), name='banished-leaderboard'),

    # AI 协同
    path('ai/toggle/', views.AIToggleView.as_view(), name='banished-ai-toggle'),
    path('ai/permissions/', views.AIPermissionsView.as_view(), name='banished-ai-permissions'),
    path('ai/action/', views.AIActionView.as_view(), name='banished-ai-action'),

    # Agent
    path('agent/tutorial/', views.AgentTutorialView.as_view(), name='banished-agent-tutorial'),
]
