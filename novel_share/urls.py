from django.urls import path
from .views import (
    SharedNovelListCreateView, SharedNovelDetailView,
    SharedChapterListCreateView, SharedChapterDetailView,
    NovelCommentListCreateView, NovelFavoriteToggleView,
    MyFavoritesView, MyNovelsView
)

urlpatterns = [
    path('novels/', SharedNovelListCreateView.as_view(), name='novel-list-create'),
    path('novels/<int:pk>/', SharedNovelDetailView.as_view(), name='novel-detail'),
    path('novels/<int:novel_id>/chapters/', SharedChapterListCreateView.as_view(), name='chapter-list-create'),
    path('chapters/<int:id>/', SharedChapterDetailView.as_view(), name='chapter-detail'),
    path('novels/<int:novel_id>/comments/', NovelCommentListCreateView.as_view(), name='comment-list-create'),
    path('novels/<int:novel_id>/favorite/', NovelFavoriteToggleView.as_view(), name='favorite-toggle'),
    path('my-favorites/', MyFavoritesView.as_view(), name='my-favorites'),
    path('my-novels/', MyNovelsView.as_view(), name='my-novels'),
]
