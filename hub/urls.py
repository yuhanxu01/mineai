from django.urls import path
from . import views

urlpatterns = [
    path('apps/', views.apps_list),
]
