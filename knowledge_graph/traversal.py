"""
知识图谱遍历与检索引擎
- 关键词搜索节点（BM25风格评分）
- BFS子图扩展
- 路径搜索
- 简化PageRank计算
- 子图格式化为RAG文本
"""
import time
from collections import defaultdict, deque


def keyword_search_nodes(kg_project_id, query, top_k=20, node_types=None):
    """
    关键词搜索节点，返回评分排序的节点列表
    评分：标签匹配=3.0，别名匹配=2.5，关键词匹配=2.0，描述匹配=1.0，importance加成
    """
    from .models import KGNode
    from django.db.models import Q

    terms = [t.strip().lower() for t in query.split() if len(t.strip()) >= 2]
    if not terms:
        qs = KGNode.objects.filter(kg_project_id=kg_project_id)
        if node_types:
            qs = qs.filter(node_type__in=node_types)
        return list(qs.order_by('-importance')[:top_k])

    # 先用DB做初步过滤
    q_filter = Q()
    for term in terms:
        q_filter |= Q(label__icontains=term)
        q_filter |= Q(description__icontains=term)

    qs = KGNode.objects.filter(kg_project_id=kg_project_id).filter(q_filter)
    if node_types:
        qs = qs.filter(node_type__in=node_types)

    # Python侧精确评分
    scored = []
    for node in qs:
        score = 0.0
        label_lower = node.label.lower()
        desc_lower = node.description.lower() if node.description else ''
        aliases_lower = [a.lower() for a in (node.aliases or [])]
        kw_lower = [k.lower() for k in (node.keywords or [])]

        for term in terms:
            if term in label_lower:
                score += 3.0
            for alias in aliases_lower:
                if term in alias:
                    score += 2.5
            for kw in kw_lower:
                if term in kw:
                    score += 2.0
            if term in desc_lower:
                score += 1.0

        score *= (1.0 + node.importance * 0.5)
        if score > 0:
            scored.append((score, node))

    scored.sort(key=lambda x: -x[0])
    return [node for _, node in scored[:top_k]]


def bfs_subgraph(kg_project_id, seed_ids, max_depth=2, max_nodes=50, edge_types=None):
    """
    从种子节点做BFS扩展，返回子图（nodes列表 + edges列表）
    支持双向扩展（in + out edges）
    """
    from .models import KGNode, KGEdge

    visited_node_ids = set(seed_ids)
    frontier = list(seed_ids)
    all_edges = []
    nodes_traversed = 0
    edges_traversed = 0

    for depth in range(max_depth):
        if not frontier or len(visited_node_ids) >= max_nodes:
            break

        # 查找边（出边+入边）
        eq = KGEdge.objects.filter(kg_project_id=kg_project_id).filter(
            source_id__in=frontier
        ) | KGEdge.objects.filter(kg_project_id=kg_project_id).filter(
            target_id__in=frontier
        )

        if edge_types:
            eq = eq.filter(relation_type__in=edge_types)

        eq = eq.select_related('source', 'target')
        edges_batch = list(eq)
        edges_traversed += len(edges_batch)

        new_frontier = []
        for edge in edges_batch:
            all_edges.append(edge)
            for nid in [edge.source_id, edge.target_id]:
                if nid not in visited_node_ids and len(visited_node_ids) < max_nodes:
                    visited_node_ids.add(nid)
                    new_frontier.append(nid)
                    nodes_traversed += 1

        frontier = new_frontier

    nodes = list(KGNode.objects.filter(id__in=visited_node_ids))

    # 去重边
    seen_edges = set()
    unique_edges = []
    for e in all_edges:
        if e.id not in seen_edges:
            seen_edges.add(e.id)
            unique_edges.append(e)

    return {
        'nodes': nodes,
        'edges': unique_edges,
        'nodes_traversed': nodes_traversed,
        'edges_traversed': edges_traversed,
    }


def find_path(kg_project_id, source_label, target_label, max_length=5):
    """
    BFS路径搜索，返回从source_label到target_label的最短路径
    返回: {'path': [node_ids], 'edges': [edge_ids], 'length': int} or None
    """
    from .models import KGNode, KGEdge

    # 查找起止节点
    source_nodes = list(KGNode.objects.filter(
        kg_project_id=kg_project_id, label__icontains=source_label
    )[:3])
    target_nodes = list(KGNode.objects.filter(
        kg_project_id=kg_project_id, label__icontains=target_label
    )[:3])

    if not source_nodes or not target_nodes:
        return None

    source_ids = {n.id for n in source_nodes}
    target_ids = {n.id for n in target_nodes}

    # BFS
    queue = deque()
    for sid in source_ids:
        queue.append(([sid], []))  # (node_path, edge_path)

    visited = set(source_ids)
    nodes_traversed = 0

    while queue:
        node_path, edge_path = queue.popleft()
        current_id = node_path[-1]

        if len(node_path) > max_length:
            continue

        # 找出边
        out_edges = list(KGEdge.objects.filter(
            kg_project_id=kg_project_id, source_id=current_id
        ))
        nodes_traversed += len(out_edges)

        for edge in out_edges:
            next_id = edge.target_id
            if next_id in target_ids:
                return {
                    'path': node_path + [next_id],
                    'edges': edge_path + [edge.id],
                    'length': len(node_path),
                    'nodes_traversed': nodes_traversed,
                }
            if next_id not in visited:
                visited.add(next_id)
                queue.append((node_path + [next_id], edge_path + [edge.id]))

    return None


def compute_node_ranks(kg_project_id, iterations=10, damping=0.85):
    """
    简化PageRank计算，更新节点importance字段
    返回更新节点数
    """
    from .models import KGNode, KGEdge

    nodes = {n.id: n for n in KGNode.objects.filter(kg_project_id=kg_project_id)}
    if not nodes:
        return 0

    n = len(nodes)
    ranks = {nid: 1.0 / n for nid in nodes}

    # 构建出边映射
    out_edges = defaultdict(list)
    for edge in KGEdge.objects.filter(kg_project_id=kg_project_id).values('source_id', 'target_id', 'weight'):
        out_edges[edge['source_id']].append((edge['target_id'], edge['weight']))

    for _ in range(iterations):
        new_ranks = {}
        for nid in nodes:
            incoming = 0.0
            for src_id, src_node in nodes.items():
                for (tgt_id, weight) in out_edges.get(src_id, []):
                    if tgt_id == nid:
                        total_weight = sum(w for _, w in out_edges.get(src_id, [])) or 1.0
                        incoming += ranks[src_id] * (weight / total_weight)
            new_ranks[nid] = (1 - damping) / n + damping * incoming
        ranks = new_ranks

    # 归一化到[0.1, 1.0]
    max_rank = max(ranks.values()) if ranks else 1.0
    min_rank = min(ranks.values()) if ranks else 0.0
    rank_range = max_rank - min_rank or 1.0

    updated = []
    for nid, node in nodes.items():
        new_importance = 0.1 + 0.9 * (ranks[nid] - min_rank) / rank_range
        node.importance = round(new_importance, 4)
        updated.append(node)

    KGNode.objects.bulk_update(updated, ['importance'])
    return len(updated)


def format_subgraph_as_text(subgraph, max_nodes=20, max_edges=30):
    """
    将子图格式化为RAG上下文文本
    适合注入到LLM prompt中
    """
    nodes = subgraph.get('nodes', [])[:max_nodes]
    edges = subgraph.get('edges', [])[:max_edges]

    if not nodes:
        return ''

    lines = ['【知识图谱上下文】']

    # 节点信息
    lines.append('节点：')
    node_map = {}
    for node in nodes:
        node_map[node.id] = node
        desc = f"（{node.description[:80]}）" if node.description else ''
        ref = f" [来源:{node.source_ref}]" if node.source_ref else ''
        lines.append(f"  · [{node.get_node_type_display()}] {node.label}{desc}{ref}")

    # 关系信息
    if edges:
        lines.append('关系：')
        for edge in edges:
            src_label = edge.source.label if hasattr(edge, 'source') and edge.source else str(edge.source_id)
            tgt_label = edge.target.label if hasattr(edge, 'target') and edge.target else str(edge.target_id)
            lines.append(f"  {src_label} --[{edge.get_relation_type_display()}]--> {tgt_label}")

    return '\n'.join(lines)


def get_node_neighbors(kg_project_id, node_id, max_neighbors=20):
    """获取节点的直接邻居（用于前端展开）"""
    from .models import KGEdge

    out_edges = list(KGEdge.objects.filter(
        kg_project_id=kg_project_id, source_id=node_id
    ).select_related('target')[:max_neighbors])

    in_edges = list(KGEdge.objects.filter(
        kg_project_id=kg_project_id, target_id=node_id
    ).select_related('source')[:max_neighbors])

    return {
        'out_edges': out_edges,
        'in_edges': in_edges,
    }
