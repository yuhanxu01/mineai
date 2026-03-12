from django.db import models
from django.conf import settings
import re


class ResearchProject(models.Model):
    """学术研究项目"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_projects')
    title = models.CharField(max_length=512, verbose_name='项目标题')
    description = models.TextField(blank=True, default='', verbose_name='项目描述')
    research_questions = models.TextField(blank=True, default='', verbose_name='研究问题')
    domain = models.CharField(max_length=256, blank=True, default='', verbose_name='研究领域')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '研究项目'

    def __str__(self):
        return self.title


class Literature(models.Model):
    """文献（论文/书籍/报告等）"""
    SOURCE_CHOICES = [
        ('ocr', 'OCR导入'),
        ('upload', 'MD上传'),
        ('manual', '手动录入'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='literatures')
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='literatures', null=True, blank=True)
    title = models.CharField(max_length=1024, verbose_name='文献标题')
    authors = models.CharField(max_length=1024, blank=True, default='', verbose_name='作者')
    year = models.CharField(max_length=20, blank=True, default='', verbose_name='年份')
    journal = models.CharField(max_length=512, blank=True, default='', verbose_name='期刊/来源')
    abstract = models.TextField(blank=True, default='', verbose_name='摘要')
    keywords_meta = models.JSONField(default=list, blank=True, verbose_name='关键词')
    content = models.TextField(blank=True, default='', verbose_name='全文内容(Markdown)')
    file_path = models.CharField(max_length=1024, blank=True, default='', verbose_name='虚拟文件路径')
    source_type = models.CharField(max_length=16, choices=SOURCE_CHOICES, default='upload')
    source_ocr_id = models.CharField(max_length=12, blank=True, default='', verbose_name='来源OCR项目ID')
    total_lines = models.IntegerField(default=0, verbose_name='总行数')
    is_indexed = models.BooleanField(default=False, verbose_name='是否已建立索引')
    is_shared = models.BooleanField(default=False, verbose_name='是否共享')
    language = models.CharField(max_length=8, default='zh', choices=[('zh', '中文'), ('en', '英文'), ('mixed', '混合')])
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '文献'

    def __str__(self):
        return self.title

    def get_file_ref(self):
        """返回用于引用的文件标识符"""
        if self.file_path:
            return self.file_path.split('/')[-1]
        return f"lit_{self.id}.md"

    def get_lines(self):
        """返回按行分割的内容列表"""
        return self.content.splitlines()


class LiteratureChunk(models.Model):
    """文献分块索引（支持精确行号引用）"""
    literature = models.ForeignKey(Literature, on_delete=models.CASCADE, related_name='chunks')
    chunk_index = models.IntegerField(verbose_name='块序号')
    line_start = models.IntegerField(verbose_name='起始行号(1-based)')
    line_end = models.IntegerField(verbose_name='结束行号(1-based)')
    content = models.TextField(verbose_name='块内容')
    heading = models.CharField(max_length=512, blank=True, default='', verbose_name='所属标题')
    chunk_type = models.CharField(max_length=16, default='text', choices=[
        ('text', '正文'),
        ('abstract', '摘要'),
        ('formula', '公式'),
        ('table', '表格'),
        ('figure', '图注'),
        ('reference', '参考文献'),
    ])
    keywords = models.JSONField(default=list, blank=True, verbose_name='关键词')
    importance = models.FloatField(default=0.5, verbose_name='重要度')
    access_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['literature', 'chunk_index']
        unique_together = ('literature', 'chunk_index')
        indexes = [
            models.Index(fields=['literature', 'line_start', 'line_end']),
            models.Index(fields=['literature', 'chunk_type']),
        ]
        verbose_name = '文献块'

    def __str__(self):
        return f"{self.literature.title} [{self.line_start}-{self.line_end}]"

    def get_citation(self):
        """返回精确引用格式，如 file.md:L45-60"""
        return f"{self.literature.get_file_ref()}:L{self.line_start}-{self.line_end}"

    def get_citation_display(self):
        """返回显示用引用格式"""
        short_title = self.literature.title[:30] + ('…' if len(self.literature.title) > 30 else '')
        return f"[{short_title}:L{self.line_start}-{self.line_end}]"


class ResearchNote(models.Model):
    """研究笔记（可关联到具体文献行范围）"""
    NOTE_TYPES = [
        ('annotation', '标注'),
        ('summary', '摘要笔记'),
        ('comment', '评论'),
        ('question', '疑问'),
        ('insight', '洞见'),
        ('connection', '关联'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_notes')
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='notes', null=True, blank=True)
    literature = models.ForeignKey(Literature, on_delete=models.CASCADE, related_name='notes', null=True, blank=True)
    note_type = models.CharField(max_length=16, choices=NOTE_TYPES, default='annotation')
    title = models.CharField(max_length=512, blank=True, default='')
    content = models.TextField(verbose_name='笔记内容')
    # 引用信息
    cited_line_start = models.IntegerField(null=True, blank=True, verbose_name='引用起始行')
    cited_line_end = models.IntegerField(null=True, blank=True, verbose_name='引用结束行')
    cited_text = models.TextField(blank=True, default='', verbose_name='引用原文')
    tags = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '研究笔记'

    def __str__(self):
        return self.title or f"Note@{self.cited_line_start}"

    def get_citation(self):
        if self.literature and self.cited_line_start:
            end = self.cited_line_end or self.cited_line_start
            return f"{self.literature.get_file_ref()}:L{self.cited_line_start}-{end}"
        return ''


class ResearchConversation(models.Model):
    """研究对话会话"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_convs')
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='conversations', null=True, blank=True)
    title = models.CharField(max_length=512, blank=True, default='新对话')
    context_literature = models.ManyToManyField(Literature, blank=True, verbose_name='上下文文献')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '研究对话'


class ResearchMessage(models.Model):
    """研究对话消息（含精确引用）"""
    ROLE_CHOICES = [('user', '用户'), ('assistant', 'AI助手'), ('system', '系统')]

    conversation = models.ForeignKey(ResearchConversation, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    content = models.TextField(verbose_name='消息内容')
    # 引用的文献块列表：[{"lit_id": 1, "chunk_id": 5, "line_start": 45, "line_end": 60, "cite_text": "..."}]
    citations = models.JSONField(default=list, blank=True, verbose_name='引用列表')
    token_usage = models.JSONField(default=dict, blank=True)
    retrieval_query = models.TextField(blank=True, default='', verbose_name='检索查询词')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = '研究消息'


class ResearchIdea(models.Model):
    """AI启发的研究灵感（必须基于文献）"""
    IDEA_TYPES = [
        ('gap', '研究空白'),
        ('contradiction', '文献矛盾'),
        ('extension', '扩展方向'),
        ('method', '方法创新'),
        ('connection', '跨领域连接'),
        ('hypothesis', '假设'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='research_ideas')
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='ideas', null=True, blank=True)
    idea_type = models.CharField(max_length=16, choices=IDEA_TYPES, default='gap')
    title = models.CharField(max_length=512)
    description = models.TextField(verbose_name='描述')
    # 必须基于具体文献片段
    evidence_chunks = models.ManyToManyField(LiteratureChunk, blank=True, verbose_name='证据片段')
    evidence_summary = models.TextField(blank=True, default='', verbose_name='证据摘要（含引用）')
    confidence = models.FloatField(default=0.5, verbose_name='置信度')
    is_starred = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = '研究灵感'


class WritingDraft(models.Model):
    """写作草稿（段落含引用标注）"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='writing_drafts')
    project = models.ForeignKey(ResearchProject, on_delete=models.CASCADE, related_name='drafts', null=True, blank=True)
    title = models.CharField(max_length=512)
    content = models.TextField(blank=True, default='', verbose_name='草稿内容(Markdown含引用)')
    outline = models.TextField(blank=True, default='', verbose_name='大纲')
    # 引用的文献列表
    referenced_literatures = models.ManyToManyField(Literature, blank=True)
    word_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '写作草稿'

    def save(self, *args, **kwargs):
        self.word_count = len(re.findall(r'[\u4e00-\u9fff]', self.content)) + len(self.content.split())
        super().save(*args, **kwargs)
