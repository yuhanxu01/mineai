from django.urls import path
from . import views

urlpatterns = [
    path('status/', views.status, name='tavern-status'),
    path('provision/', views.provision, name='tavern-provision'),
    path('admin/config/', views.admin_config, name='tavern-admin-config'),
    path('admin/accounts/', views.admin_accounts, name='tavern-admin-accounts'),
]
