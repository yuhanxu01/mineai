from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/core/', include('core.urls')),
    path('api/memory/', include('memory.urls')),
    path('api/novel/', include('novel.urls')),
    path('api/platform/', include('hub.urls')),
    path('api/share/', include('novel_share.urls')),
    path('api/ocr/', include('ocr_studio.urls')),
    path('api/paper/', include('paper_lab.urls')),
    path('share/', TemplateView.as_view(template_name='share_index.html')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('', TemplateView.as_view(template_name='index.html')),
] + static(settings.MEDIA_URL, document_root=getattr(settings, 'MEDIA_ROOT', 'media'))
