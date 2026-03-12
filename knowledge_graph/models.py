from django.db import models
from django.conf import settings


class KGProject(models.Model):
    """知识图谱项目"""
    SOURCE_APP_CHOICES = [
        ('paper_lab', '学术研究站'),
        ('memoryforge', '记忆熔炉'),
        ('api', 'API调用'),
        ('manual', '手动创建'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kg_projects')
    title = models.CharField(max_length=512, verbose_name='图谱名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    source_app = models.CharField(max_length=32, choices=SOURCE_APP_CHOICES, default='manual')
    source_project_id = models.IntegerField(null=True, blank=True, verbose_name='来源项目ID')
    is_shared = models.BooleanField(default=False, verbose_name='是否共享')
    node_count = models.IntegerField(default=0, verbose_name='节点数缓存')
    edge_count = models.IntegerField(default=0, verbose_name='边数缓存')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = '知识图谱项目'

    def __str__(self):
        return self.title

    def refresh_counts(self):
        self.node_count = self.nodes.count()
        self.edge_count = self.edges.count()
        self.save(update_fields=['node_count', 'edge_count', 'updated_at'])


class KGNode(models.Model):
    """知识图谱节点"""
    NODE_TYPE_CHOICES = [
        ('concept', '概念'),
        ('entity', '实体'),
        ('event', '事件'),
        ('claim', '论断'),
        ('method', '方法'),
        ('result', '结论'),
        ('character', '人物'),
        ('paper', '论文'),
        ('place', '地点'),
        ('term', '术语'),
        ('memory', '记忆'),
    ]

    kg_project = models.ForeignKey(KGProject, on_delete=models.CASCADE, related_name='nodes')
    label = models.CharField(max_length=512, verbose_name='节点标签', db_index=True)
    node_type = models.CharField(max_length=16, choices=NODE_TYPE_CHOICES, default='concept', db_index=True)
    description = models.TextField(blank=True, default='', verbose_name='描述')
    aliases = models.JSONField(default=list, blank=True, verbose_name='别名列表')
    keywords = models.JSONField(default=list, blank=True, verbose_name='关键词')
    importance = models.FloatField(default=0.5, verbose_name='重要度(PageRank)')
    visit_count = models.IntegerField(default=0, verbose_name='访问次数')
    source_ref = models.CharField(max_length=1024, blank=True, default='', verbose_name='来源引用(file.md:L45-60)')
    source_lit_id = models.IntegerField(null=True, blank=True, verbose_name='来源文献ID')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-importance', 'label']
        indexes = [
            models.Index(fields=['kg_project', 'label']),
            models.Index(fields=['kg_project', 'node_type']),
            models.Index(fields=['kg_project', 'importance']),
        ]
        verbose_name = '知识节点'

    def __str__(self):
        return f"{self.label} ({self.node_type})"

    def to_cytoscape(self):
        """返回Cytoscape.js节点格式"""
        return {
            'data': {
                'id': str(self.id),
                'label': self.label,
                'type': self.node_type,
                'importance': self.importance,
                'description': self.description[:200] if self.description else '',
                'source_ref': self.source_ref,
            }
        }


class KGEdge(models.Model):
    """知识图谱边（有向关系）"""
    RELATION_CHOICES = [
        ('supports', '支持'),
        ('contradicts', '矛盾'),
        ('causes', '导致'),
        ('extends', '扩展'),
        ('related_to', '相关'),
        ('defines', '定义'),
        ('exemplifies', '举例'),
        ('cites', '引用'),
        ('part_of', '组成'),
        ('leads_to', '推导'),
        ('opposes', '对立'),
        ('has_method', '使用方法'),
        ('has_result', '得出结论'),
        ('is_a', '属于'),
        ('instance_of', '实例化'),
        ('precedes', '先于'),
        ('follows', '后于'),
    ]

    kg_project = models.ForeignKey(KGProject, on_delete=models.CASCADE, related_name='edges')
    source = models.ForeignKey(KGNode, on_delete=models.CASCADE, related_name='out_edges')
    target = models.ForeignKey(KGNode, on_delete=models.CASCADE, related_name='in_edges')
    relation_type = models.CharField(max_length=16, choices=RELATION_CHOICES, default='related_to')
    weight = models.FloatField(default=1.0, verbose_name='权重')
    confidence = models.FloatField(default=0.8, verbose_name='置信度')
    description = models.TextField(blank=True, default='', verbose_name='关系描述')
    source_citation = models.CharField(max_length=1024, blank=True, default='', verbose_name='来源引用')
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['kg_project', 'source', 'target']),
            models.Index(fields=['kg_project', 'relation_type']),
            models.Index(fields=['source', 'relation_type']),
            models.Index(fields=['target', 'relation_type']),
        ]
        verbose_name = '知识边'

    def __str__(self):
        return f"{self.source.label} --[{self.relation_type}]--> {self.target.label}"

    def to_cytoscape(self):
        """返回Cytoscape.js边格式"""
        return {
            'data': {
                'id': f"e{self.id}",
                'source': str(self.source_id),
                'target': str(self.target_id),
                'relation': self.relation_type,
                'relation_label': self.get_relation_type_display(),
                'weight': self.weight,
                'confidence': self.confidence,
                'description': self.description[:200] if self.description else '',
            }
        }


class KGCallLog(models.Model):
    """知识图谱调用日志（资源消耗统计）"""
    OPERATION_CHOICES = [
        ('extract_text', '文本提取节点'),
        ('add_node', '添加节点'),
        ('add_edge', '添加边'),
        ('query_subgraph', '查询子图'),
        ('search_nodes', '搜索节点'),
        ('find_path', '路径搜索'),
        ('batch_extract', '批量提取'),
        ('get_context', '获取RAG上下文'),
        ('compute_rank', '计算节点排名'),
        ('bfs_traverse', 'BFS遍历'),
    ]

    CALLER_APP_CHOICES = [
        ('paper_lab', '学术研究站'),
        ('memoryforge', '记忆熔炉'),
        ('api', '直接API'),
        ('manual', '手动操作'),
        ('system', '系统内部'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='kg_call_logs')
    kg_project = models.ForeignKey(KGProject, on_delete=models.CASCADE, related_name='call_logs', null=True, blank=True)
    operation = models.CharField(max_length=32, choices=OPERATION_CHOICES)
    caller_app = models.CharField(max_length=16, choices=CALLER_APP_CHOICES, default='api')
    # 输入统计
    input_length = models.IntegerField(default=0, verbose_name='输入文本长度')
    # 图谱变更
    nodes_created = models.IntegerField(default=0, verbose_name='新建节点数')
    edges_created = models.IntegerField(default=0, verbose_name='新建边数')
    # 遍历统计
    nodes_traversed = models.IntegerField(default=0, verbose_name='遍历节点数')
    edges_traversed = models.IntegerField(default=0, verbose_name='遍历边数')
    result_nodes = models.IntegerField(default=0, verbose_name='结果节点数')
    # 性能指标
    duration_ms = models.IntegerField(default=0, verbose_name='耗时(ms)')
    llm_tokens_input = models.IntegerField(default=0, verbose_name='LLM输入Token')
    llm_tokens_output = models.IntegerField(default=0, verbose_name='LLM输出Token')
    memory_bytes_estimated = models.IntegerField(default=0, verbose_name='估计内存(bytes)')
    # 状态
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['kg_project', 'operation']),
            models.Index(fields=['caller_app', 'created_at']),
        ]
        verbose_name = '图谱调用日志'

    def __str__(self):
        return f"{self.user} | {self.operation} | {self.duration_ms}ms"

    @classmethod
    def record(cls, user, kg_project, operation, caller_app='api', **kwargs):
        """便捷记录方法"""
        return cls.objects.create(
            user=user,
            kg_project=kg_project,
            operation=operation,
            caller_app=caller_app,
            **kwargs
        )
