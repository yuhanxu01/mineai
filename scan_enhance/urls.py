from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.StatusView.as_view()),
    path('uploads/', views.UserUploadListCreateView.as_view()),
    path('uploads/<int:pk>/', views.UserUploadDetailView.as_view()),
]
