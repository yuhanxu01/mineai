from django.urls import path
from . import views

urlpatterns = [
    # Public
    path('plugins/', views.plugin_list, name='plugin-list'),

    # Authenticated: create
    path('plugins/create/', views.plugin_create, name='plugin-create'),

    # Author: my plugins
    path('my/', views.my_plugins, name='my-plugins'),

    # Plugin detail (GET/PUT/DELETE)
    path('plugins/<int:pk>/', views.plugin_detail, name='plugin-detail'),
    path('plugins/<int:pk>/visibility/', views.plugin_visibility, name='plugin-visibility'),

    # Code Plugin: serve HTML with SDK
    path('plugins/<int:pk>/serve/', views.plugin_serve, name='plugin-serve'),

    # Proxies
    path('plugins/<int:pk>/proxy/llm/', views.plugin_proxy_llm, name='plugin-proxy-llm'),
    path('plugins/<int:pk>/proxy/memory/', views.plugin_proxy_memory, name='plugin-proxy-memory'),

    # KV data
    path('plugins/<int:pk>/data/', views.plugin_data, name='plugin-data'),
    path('templates/lan-transfer/install/', views.install_lan_transfer_template, name='plugin-template-lan-transfer-install'),

    # Admin
    path('admin/pending/', views.admin_pending, name='admin-pending'),
    path('admin/<int:pk>/review/', views.admin_review, name='admin-review'),
]
