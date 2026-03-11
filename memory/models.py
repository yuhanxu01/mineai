from django.db import models


class MemoryNode(models.Model):
    LEVEL_CHOICES = [
        (0, '世界'),    # global story overview
        (1, '大陆'),    # major arcs / acts
        (2, '王国'),    # chapters
        (3, '城池'),    # scenes
        (4, '街巷'),    # raw detail chunks
    ]
    TYPE_CHOICES = [
        ('narrative', '叙事'),
        ('character', '角色'),
        ('worldbuild', '世界观'),
        ('plot', '剧情'),
        ('style', '风格'),
        ('relation', '关系'),
        ('foreshadow', '伏笔'),
        ('setting', '设定'),
    ]

    project_id = models.IntegerField(db_index=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    level = models.IntegerField(choices=LEVEL_CHOICES, db_index=True)
    node_type = models.CharField(max_length=16, choices=TYPE_CHOICES, default='narrative')
    title = models.CharField(max_length=512)
    summary = models.TextField()
    content = models.TextField(blank=True, default='')
    importance = models.FloatField(default=0.5)
    access_count = models.IntegerField(default=0)
    version = models.IntegerField(default=1)
    story_time = models.CharField(max_length=256, blank=True, default='')
    chapter_index = models.IntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['level', '-importance', '-updated_at']
        indexes = [
            models.Index(fields=['project_id', 'level']),
            models.Index(fields=['project_id', 'node_type']),
            models.Index(fields=['project_id', 'chapter_index']),
        ]

    def __str__(self):
        return f"[L{self.level}] {self.title}"

    @property
    def level_name(self):
        return dict(self.LEVEL_CHOICES).get(self.level, '未知')


class MemorySnapshot(models.Model):
    node = models.ForeignKey(MemoryNode, on_delete=models.CASCADE, related_name='snapshots')
    version = models.IntegerField()
    summary = models.TextField()
    content = models.TextField(blank=True, default='')
    chapter_index = models.IntegerField(default=0)
    change_reason = models.CharField(max_length=512, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['node', 'version']
        unique_together = ('node', 'version')


class MemoryLink(models.Model):
    LINK_TYPES = [
        ('parent_child', '父子'),
        ('temporal', '时序'),
        ('causal', '因果'),
        ('semantic', '语义'),
        ('character', '角色'),
        ('conflict', '冲突'),
        ('evolution', '演变'),
        ('foreshadow', '伏笔'),
    ]

    project_id = models.IntegerField(db_index=True)
    source = models.ForeignKey(MemoryNode, on_delete=models.CASCADE, related_name='outgoing_links')
    target = models.ForeignKey(MemoryNode, on_delete=models.CASCADE, related_name='incoming_links')
    link_type = models.CharField(max_length=16, choices=LINK_TYPES)
    weight = models.FloatField(default=1.0)
    description = models.CharField(max_length=512, blank=True, default='')

    class Meta:
        unique_together = ('source', 'target', 'link_type')


class Character(models.Model):
    project_id = models.IntegerField(db_index=True)
    name = models.CharField(max_length=256)
    aliases = models.JSONField(default=list, blank=True)
    description = models.TextField()
    traits = models.JSONField(default=list, blank=True)
    backstory = models.TextField(blank=True, default='')
    current_state = models.TextField(blank=True, default='')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        unique_together = ('project_id', 'name')

    def __str__(self):
        return self.name


class CharacterSnapshot(models.Model):
    character = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='snapshots')
    chapter_index = models.IntegerField(default=0)
    state = models.TextField()
    traits = models.JSONField(default=list, blank=True)
    beliefs = models.TextField(blank=True, default='')
    goals = models.TextField(blank=True, default='')
    relationships = models.JSONField(default=dict, blank=True)
    change_description = models.CharField(max_length=512, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['character', 'chapter_index']


class CharacterRelation(models.Model):
    project_id = models.IntegerField(db_index=True)
    char_a = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='relations_as_a')
    char_b = models.ForeignKey(Character, on_delete=models.CASCADE, related_name='relations_as_b')
    relation_type = models.CharField(max_length=128)
    description = models.TextField(blank=True, default='')
    evolution = models.JSONField(default=list, blank=True)

    class Meta:
        unique_together = ('char_a', 'char_b')


class TimelineEvent(models.Model):
    EVENT_TYPES = [
        ('plot', '剧情'),
        ('character', '角色变化'),
        ('worldbuild', '世界观'),
        ('relation', '关系变化'),
        ('foreshadow', '伏笔'),
        ('reveal', '揭示'),
        ('turning', '转折'),
    ]

    project_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=16, choices=EVENT_TYPES, default='plot')
    chapter_index = models.IntegerField(default=0)
    story_time = models.CharField(max_length=256, blank=True, default='')
    title = models.CharField(max_length=512)
    description = models.TextField()
    characters_involved = models.JSONField(default=list, blank=True)
    impact = models.TextField(blank=True, default='')
    memory_node = models.ForeignKey(MemoryNode, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['chapter_index', 'created_at']
        indexes = [
            models.Index(fields=['project_id', 'chapter_index']),
            models.Index(fields=['project_id', 'event_type']),
        ]
