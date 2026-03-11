from rest_framework import serializers
from accounts.models import User
from .models import SharedNovel, SharedChapter, NovelComment, NovelFavorite

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email']


class SharedChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedChapter
        fields = ['id', 'novel', 'number', 'title', 'content', 'word_count', 'created_at', 'updated_at']
        read_only_fields = ['novel', 'word_count']


class SharedChapterListSerializer(serializers.ModelSerializer):
    class Meta:
        model = SharedChapter
        fields = ['id', 'novel', 'number', 'title', 'word_count', 'created_at']


class SharedNovelSerializer(serializers.ModelSerializer):
    author = UserBasicSerializer(read_only=True)
    chapter_count = serializers.SerializerMethodField()
    total_words = serializers.SerializerMethodField()
    chapters = SharedChapterListSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    rating_avg = serializers.SerializerMethodField()

    class Meta:
        model = SharedNovel
        fields = ['id', 'author', 'title', 'synopsis', 'cover', 'bg_color', 'font_family', 'status', 
                  'chapter_count', 'total_words', 'chapters', 'is_favorited', 'rating_avg', 'created_at', 'updated_at']
        read_only_fields = ['author']

    def get_chapter_count(self, obj):
        return obj.chapters.count()

    def get_total_words(self, obj):
        return sum(c.word_count for c in obj.chapters.all())

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return NovelFavorite.objects.filter(user=request.user, novel=obj).exists()
        return False

    def get_rating_avg(self, obj):
        ratings = obj.comments.filter(chapter__isnull=True, paragraph_index__isnull=True, rating__isnull=False)
        if not ratings.exists():
            return 0
        return sum(r.rating for r in ratings) / ratings.count()


class NovelCommentSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    
    class Meta:
        model = NovelComment
        fields = ['id', 'user', 'novel', 'chapter', 'paragraph_index', 'content', 'rating', 'created_at']
        read_only_fields = ['user', 'novel', 'chapter']


class NovelFavoriteSerializer(serializers.ModelSerializer):
    novel = SharedNovelSerializer(read_only=True)
    
    class Meta:
        model = NovelFavorite
        fields = ['id', 'user', 'novel', 'created_at']
        read_only_fields = ['user']
