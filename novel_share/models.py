from django.db import models
from django.conf import settings

class SharedNovel(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shared_novels', verbose_name='作者')
    title = models.CharField(max_length=255, verbose_name='书名')
    synopsis = models.TextField(blank=True, verbose_name='简介')
    cover = models.ImageField(upload_to='novel_covers/', null=True, blank=True, verbose_name='封面')
    
    # 偏好设置
    bg_color = models.CharField(max_length=50, default='#f5f5dc', verbose_name='背景颜色') # 例如羊皮纸色
    font_family = models.CharField(max_length=100, default='sans-serif', verbose_name='字体')
    
    status = models.CharField(max_length=20, default='published', choices=[
        ('draft', '草稿'),
        ('published', '已发布')
    ], verbose_name='状态')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '共享小说'
        verbose_name_plural = '共享小说列表'

    def __str__(self):
        return self.title


class SharedChapter(models.Model):
    novel = models.ForeignKey(SharedNovel, on_delete=models.CASCADE, related_name='chapters', verbose_name='所属小说')
    number = models.PositiveIntegerField(verbose_name='章节号')
    title = models.CharField(max_length=255, verbose_name='章节标题')
    content = models.TextField(verbose_name='正文')
    word_count = models.PositiveIntegerField(default=0, verbose_name='字数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        ordering = ['number']
        unique_together = ('novel', 'number')
        verbose_name = '共享章节'
        verbose_name_plural = '共享章节列表'

    def __str__(self):
        return f"{self.novel.title} - 第{self.number}章: {self.title}"

    def save(self, *args, **kwargs):
        self.word_count = len(self.content)
        super().save(*args, **kwargs)


class NovelComment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='novel_comments', verbose_name='用户')
    novel = models.ForeignKey(SharedNovel, on_delete=models.CASCADE, related_name='comments', verbose_name='小说')
    
    # 可选字段：若指定 chapter，则为章节评论
    chapter = models.ForeignKey(SharedChapter, on_delete=models.CASCADE, null=True, blank=True, related_name='comments', verbose_name='章节')
    
    # 可选字段：若指定 paragraph_index（配合 chapter使用），则为段评
    paragraph_index = models.IntegerField(null=True, blank=True, verbose_name='段落索引')
    
    content = models.TextField(verbose_name='评论内容')
    rating = models.PositiveIntegerField(null=True, blank=True, verbose_name='评分(1-5)') # 整书评论时可评分
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='评论时间')

    class Meta:
        ordering = ['-created_at']
        verbose_name = '小说评论'
        verbose_name_plural = '小说评论列表'

    def __str__(self):
        target = f"《{self.novel.title}》"
        if self.chapter and self.paragraph_index is not None:
            target += f" 第{self.chapter.number}章 段落{self.paragraph_index}"
        elif self.chapter:
            target += f" 第{self.chapter.number}章"
        return f"{self.user.email} 评论于 {target}"


class NovelFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='novel_favorites', verbose_name='用户')
    novel = models.ForeignKey(SharedNovel, on_delete=models.CASCADE, related_name='favorited_by', verbose_name='小说')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='收藏时间')

    class Meta:
        unique_together = ('user', 'novel')
        ordering = ['-created_at']
        verbose_name = '小说收藏'
        verbose_name_plural = '小说收藏列表'

    def __str__(self):
        return f"{self.user.email} 收藏 《{self.novel.title}》"
