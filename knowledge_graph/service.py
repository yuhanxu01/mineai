"""
知识图谱跨应用集成服务层
其他应用通过此模块调用知识图谱功能

使用示例：
    from knowledge_graph.service import get_or_create_project, extract_from_text, get_context_for_rag

    # 为学术研究项目创建图谱
    kg = get_or_create_project(user, title='我的研究图谱', source_app='paper_lab', source_project_id=3)

    # 从文本提取知识
    result = extract_from_text(user, kg.id, text, source_ref='paper.md:L1-50', caller_app='paper_lab')

    # 获取RAG上下文
    context = get_context_for_rag(user, kg.id, query='量子纠缠', caller_app='paper_lab')
"""
import time
import sys


def get_or_create_project(user, title, source_app='api', source_project_id=None, description=''):
    """获取或创建与某应用关联的知识图谱项目"""
    from .models import KGProject

    if source_app and source_project_id:
        proj = KGProject.objects.filter(
            user=user, source_app=source_app, source_project_id=source_project_id
        ).first()
        if proj:
            return proj

    return KGProject.objects.create(
        user=user,
        title=title,
        description=description,
        source_app=source_app,
        source_project_id=source_project_id,
    )


def add_node(user, kg_project_id, label, node_type='concept', description='',
             keywords=None, aliases=None, source_ref='', source_lit_id=None,
             caller_app='api'):
    """
    添加或更新节点（同一图谱内label唯一）
    返回 (node, created)
    """
    from .models import KGNode, KGProject, KGCallLog
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id, user=user)
    except KGProject.DoesNotExist:
        return None, False

    node, created = KGNode.objects.get_or_create(
        kg_project=kg,
        label=label,
        defaults={
            'node_type': node_type,
            'description': description,
            'keywords': keywords or [],
            'aliases': aliases or [],
            'source_ref': source_ref,
            'source_lit_id': source_lit_id,
        }
    )

    if not created and description and not node.description:
        node.description = description
        node.save(update_fields=['description', 'updated_at'])

    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='add_node', caller_app=caller_app,
        nodes_created=1 if created else 0,
        duration_ms=duration_ms,
    )

    if created:
        kg.node_count = kg.nodes.count()
        kg.save(update_fields=['node_count', 'updated_at'])

    return node, created


def add_edge(user, kg_project_id, source_node_id, target_node_id,
             relation_type='related_to', weight=1.0, confidence=0.8,
             description='', source_citation='', caller_app='api'):
    """
    添加边（允许重复，但同source+target+relation不重复）
    返回 (edge, created)
    """
    from .models import KGEdge, KGProject, KGCallLog
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id, user=user)
    except KGProject.DoesNotExist:
        return None, False

    edge, created = KGEdge.objects.get_or_create(
        kg_project=kg,
        source_id=source_node_id,
        target_id=target_node_id,
        relation_type=relation_type,
        defaults={
            'weight': weight,
            'confidence': confidence,
            'description': description,
            'source_citation': source_citation,
        }
    )

    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='add_edge', caller_app=caller_app,
        edges_created=1 if created else 0,
        duration_ms=duration_ms,
    )

    if created:
        kg.edge_count = kg.edges.count()
        kg.save(update_fields=['edge_count', 'updated_at'])

    return edge, created


def search_nodes(user, kg_project_id, query, top_k=10, node_types=None, caller_app='api'):
    """
    搜索节点，返回评分排序的节点列表及统计信息
    """
    from .models import KGProject, KGCallLog
    from .traversal import keyword_search_nodes
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id)
        # 权限检查
        if kg.user_id != user.id and not kg.is_shared:
            return []
    except KGProject.DoesNotExist:
        return []

    nodes = keyword_search_nodes(kg_project_id, query, top_k=top_k, node_types=node_types)
    duration_ms = int((time.time() - t0) * 1000)

    # 增加visit_count
    if nodes:
        from .models import KGNode
        from django.db.models import F
        KGNode.objects.filter(id__in=[n.id for n in nodes]).update(
            visit_count=F('visit_count') + 1
        )

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='search_nodes', caller_app=caller_app,
        input_length=len(query),
        result_nodes=len(nodes),
        nodes_traversed=len(nodes),
        duration_ms=duration_ms,
    )

    return nodes


def query_subgraph(user, kg_project_id, seed_labels=None, seed_ids=None,
                   max_depth=2, max_nodes=50, edge_types=None, caller_app='api'):
    """
    从种子节点/标签查询子图
    返回 {'nodes': [...], 'edges': [...], 'stats': {...}}
    """
    from .models import KGProject, KGCallLog
    from .traversal import keyword_search_nodes, bfs_subgraph
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id)
        if kg.user_id != user.id and not kg.is_shared:
            return {'nodes': [], 'edges': [], 'stats': {}}
    except KGProject.DoesNotExist:
        return {'nodes': [], 'edges': [], 'stats': {}}

    # 收集种子ID
    all_seed_ids = list(seed_ids or [])
    if seed_labels:
        for label in seed_labels:
            found = keyword_search_nodes(kg_project_id, label, top_k=3)
            all_seed_ids.extend([n.id for n in found])

    if not all_seed_ids:
        # 返回最重要的节点
        from .models import KGNode
        top_nodes = list(KGNode.objects.filter(kg_project_id=kg_project_id)
                         .order_by('-importance')[:max_nodes])
        all_seed_ids = [n.id for n in top_nodes[:5]]

    result = bfs_subgraph(kg_project_id, all_seed_ids, max_depth=max_depth,
                          max_nodes=max_nodes, edge_types=edge_types)
    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='query_subgraph', caller_app=caller_app,
        nodes_traversed=result['nodes_traversed'],
        edges_traversed=result['edges_traversed'],
        result_nodes=len(result['nodes']),
        duration_ms=duration_ms,
    )

    return {
        'nodes': result['nodes'],
        'edges': result['edges'],
        'stats': {
            'nodes_count': len(result['nodes']),
            'edges_count': len(result['edges']),
            'nodes_traversed': result['nodes_traversed'],
            'edges_traversed': result['edges_traversed'],
            'duration_ms': duration_ms,
        }
    }


def get_context_for_rag(user, kg_project_id, query, max_nodes=15, caller_app='api'):
    """
    获取知识图谱RAG上下文，用于注入LLM prompt
    返回格式化文本字符串
    """
    from .models import KGProject, KGCallLog
    from .traversal import keyword_search_nodes, bfs_subgraph, format_subgraph_as_text
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id)
        if kg.user_id != user.id and not kg.is_shared:
            return ''
    except KGProject.DoesNotExist:
        return ''

    # 搜索相关节点
    seed_nodes = keyword_search_nodes(kg_project_id, query, top_k=5)
    if not seed_nodes:
        return ''

    seed_ids = [n.id for n in seed_nodes]

    # 1层BFS扩展
    subgraph = bfs_subgraph(kg_project_id, seed_ids, max_depth=1, max_nodes=max_nodes)
    context_text = format_subgraph_as_text(subgraph)

    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='get_context', caller_app=caller_app,
        input_length=len(query),
        nodes_traversed=subgraph['nodes_traversed'],
        edges_traversed=subgraph['edges_traversed'],
        result_nodes=len(subgraph['nodes']),
        duration_ms=duration_ms,
    )

    return context_text


def find_path_between(user, kg_project_id, source_label, target_label, caller_app='api'):
    """查找两概念之间的关系路径"""
    from .models import KGProject, KGCallLog, KGNode, KGEdge
    from .traversal import find_path
    import time

    t0 = time.time()
    try:
        kg = KGProject.objects.get(id=kg_project_id)
        if kg.user_id != user.id and not kg.is_shared:
            return None
    except KGProject.DoesNotExist:
        return None

    result = find_path(kg_project_id, source_label, target_label)
    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='find_path', caller_app=caller_app,
        input_length=len(source_label) + len(target_label),
        nodes_traversed=result['nodes_traversed'] if result else 0,
        duration_ms=duration_ms,
    )

    if result:
        nodes = list(KGNode.objects.filter(id__in=result['path']))
        edges = list(KGEdge.objects.filter(id__in=result['edges']))
        result['node_objects'] = nodes
        result['edge_objects'] = edges

    return result


def extract_from_text(user, kg_project_id, text, source_ref='', caller_app='api',
                      source_lit_id=None):
    """
    使用LLM从文本提取知识节点和关系，添加到图谱
    这是agent.py的高层封装
    """
    from .agent import extract_kg_from_text
    return extract_kg_from_text(
        user=user,
        kg_project_id=kg_project_id,
        text=text,
        source_ref=source_ref,
        caller_app=caller_app,
        source_lit_id=source_lit_id,
    )

