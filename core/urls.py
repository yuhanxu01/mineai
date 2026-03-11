from django.urls import path
from core.views import ConfigView, LogsView, SimpleChatStreamView

urlpatterns = [
    path('config/', ConfigView.as_view()),
    path('logs/', LogsView.as_view()),
    path('chat-stream/', SimpleChatStreamView.as_view()),
]
