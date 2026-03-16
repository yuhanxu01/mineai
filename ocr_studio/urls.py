from django.urls import path
from . import views

urlpatterns = [
    path('recognize/', views.OCRRecognizeView.as_view(), name='ocr_recognize'),
]
