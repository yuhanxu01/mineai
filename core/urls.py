from django.urls import path
from core.views import ConfigView, LogsView

urlpatterns = [
    path('config/', ConfigView.as_view()),
    path('logs/', LogsView.as_view()),
]
