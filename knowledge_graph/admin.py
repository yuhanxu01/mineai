from django.contrib import admin
from .models import KGProject, KGNode, KGEdge, KGCallLog


@admin.register(KGProject)
class KGProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'user', 'source_app', 'node_count', 'edge_count', 'created_at']
    list_filter = ['source_app', 'is_shared']
    search_fields = ['title', 'user__username']


@admin.register(KGNode)
class KGNodeAdmin(admin.ModelAdmin):
    list_display = ['label', 'node_type', 'importance', 'visit_count', 'kg_project']
    list_filter = ['node_type']
    search_fields = ['label', 'description']


@admin.register(KGEdge)
class KGEdgeAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'relation_type', 'weight', 'confidence', 'kg_project']
    list_filter = ['relation_type']


@admin.register(KGCallLog)
class KGCallLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'operation', 'caller_app', 'duration_ms', 'nodes_created',
                    'edges_created', 'llm_tokens_input', 'success', 'created_at']
    list_filter = ['operation', 'caller_app', 'success']
    readonly_fields = ['created_at']
