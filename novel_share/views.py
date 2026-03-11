from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import SharedNovel, SharedChapter, NovelComment, NovelFavorite
from .serializers import (
    SharedNovelSerializer, SharedChapterSerializer, 
    NovelCommentSerializer, NovelFavoriteSerializer,
    SharedChapterListSerializer
)

class IsAuthorOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class SharedNovelListCreateView(generics.ListCreateAPIView):
    queryset = SharedNovel.objects.filter(status='published')
    serializer_class = SharedNovelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = SharedNovel.objects.filter(status='published')
        # Allow authors to see their own drafts
        if self.request.user.is_authenticated:
            user_drafts = SharedNovel.objects.filter(author=self.request.user, status='draft')
            qs = qs | user_drafts
        return qs.distinct().order_by('-updated_at')

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class SharedNovelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SharedNovel.objects.all()
    serializer_class = SharedNovelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]

    def get_queryset(self):
        qs = SharedNovel.objects.filter(status='published')
        if self.request.user.is_authenticated:
            user_drafts = SharedNovel.objects.filter(author=self.request.user, status='draft')
            qs = qs | user_drafts
        return qs.distinct()


class SharedChapterListCreateView(generics.ListCreateAPIView):
    serializer_class = SharedChapterListSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        novel_id = self.kwargs['novel_id']
        novel = get_object_or_404(SharedNovel, id=novel_id)
        return SharedChapter.objects.filter(novel=novel).order_by('number')

    def perform_create(self, serializer):
        novel_id = self.kwargs['novel_id']
        novel = get_object_or_404(SharedNovel, id=novel_id)
        if novel.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the author can add chapters.")
        serializer.save(novel=novel)


class SharedChapterDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SharedChapter.objects.all()
    serializer_class = SharedChapterSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'id'

    def get_object(self):
        obj = super().get_object()
        if self.request.method not in permissions.SAFE_METHODS and obj.novel.author != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only the author can modify chapters.")
        return obj


class NovelCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = NovelCommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        novel_id = self.kwargs['novel_id']
        chapter_id = self.request.query_params.get('chapter_id')
        para_index = self.request.query_params.get('paragraph_index')

        qs = NovelComment.objects.filter(novel_id=novel_id)
        if chapter_id:
            qs = qs.filter(chapter_id=chapter_id)
            if para_index is not None:
                qs = qs.filter(paragraph_index=para_index)
            else:
                qs = qs.filter(paragraph_index__isnull=True)
        else:
            qs = qs.filter(chapter__isnull=True)
            
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        novel_id = self.kwargs['novel_id']
        novel = get_object_or_404(SharedNovel, id=novel_id)
        chapter_id = self.request.data.get('chapter_id')
        
        chapter = None
        if chapter_id:
            chapter = get_object_or_404(SharedChapter, id=chapter_id, novel=novel)
            
        serializer.save(user=self.request.user, novel=novel, chapter=chapter)


class NovelFavoriteToggleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, novel_id):
        novel = get_object_or_404(SharedNovel, id=novel_id)
        fav, created = NovelFavorite.objects.get_or_create(user=request.user, novel=novel)
        if not created:
            fav.delete()
            return Response({'status': 'unfavorited', 'novel_id': novel_id})
        return Response({'status': 'favorited', 'novel_id': novel_id})


class MyFavoritesView(generics.ListAPIView):
    serializer_class = NovelFavoriteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NovelFavorite.objects.filter(user=self.request.user).order_by('-created_at')

class MyNovelsView(generics.ListAPIView):
    serializer_class = SharedNovelSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SharedNovel.objects.filter(author=self.request.user).order_by('-updated_at')
