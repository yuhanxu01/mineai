from django.urls import path
from . import views

urlpatterns = [
    path('test/', views.TestView.as_view(), name='ssh-test'),
    path('ls/', views.LsView.as_view(), name='ssh-ls'),
    path('read/', views.ReadView.as_view(), name='ssh-read'),
    path('write/', views.WriteView.as_view(), name='ssh-write'),
    path('upload/', views.UploadView.as_view(), name='ssh-upload'),
    path('download/', views.DownloadView.as_view(), name='ssh-download'),
    path('proxy/', views.ProxyView.as_view(), name='ssh-proxy'),
    path('delete/', views.DeleteView.as_view(), name='ssh-delete'),
    path('mkdir/', views.MkdirView.as_view(), name='ssh-mkdir'),
    path('rename/', views.RenameView.as_view(), name='ssh-rename'),
    path('zip-meta/', views.ZipMetaView.as_view(), name='ssh-zip-meta'),
    path('zip/', views.ZipDownloadView.as_view(), name='ssh-zip'),
    path('exec/', views.ExecView.as_view(), name='ssh-exec'),
    path('chmod/', views.ChmodView.as_view(), name='ssh-chmod'),
    path('copy/', views.CopyView.as_view(), name='ssh-copy'),
    path('term/open/', views.TermOpenView.as_view(), name='ssh-term-open'),
    path('term/input/', views.TermInputView.as_view(), name='ssh-term-input'),
    path('term/resize/', views.TermResizeView.as_view(), name='ssh-term-resize'),
    path('term/stream/<str:session_id>/', views.TermStreamView.as_view(), name='ssh-term-stream'),
    path('term/close/', views.TermCloseView.as_view(), name='ssh-term-close'),
]
