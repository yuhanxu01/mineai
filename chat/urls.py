from django.urls import path
from .views import ConversationListCreateView, ConversationDetailView, ChatStreamView

urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<int:pk>/', ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<int:pk>/chat/', ChatStreamView.as_view(), name='conversation-chat'),
]
