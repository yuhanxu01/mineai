"""
知识图谱LLM智能体
- 从文本自动提取节点和关系
- 实体消歧与合并
- 流式知识构建
"""
import json
import time
import re
import logging

logger = logging.getLogger(__name__)

# 支持的节点类型
NODE_TYPE_MAP = {
    '概念': 'concept', '实体': 'entity', '事件': 'event',
    '论断': 'claim', '方法': 'method', '结论': 'result',
    '人物': 'character', '论文': 'paper', '地点': 'place',
    '术语': 'term', '记忆': 'memory',
    # English
    'concept': 'concept', 'entity': 'entity', 'event': 'event',
    'claim': 'claim', 'method': 'method', 'result': 'result',
    'character': 'character', 'paper': 'paper', 'place': 'place',
    'term': 'term', 'memory': 'memory',
}

RELATION_MAP = {
    '支持': 'supports', '矛盾': 'contradicts', '导致': 'causes',
    '扩展': 'extends', '相关': 'related_to', '定义': 'defines',
    '举例': 'exemplifies', '引用': 'cites', '组成': 'part_of',
    '推导': 'leads_to', '对立': 'opposes', '使用方法': 'has_method',
    '得出结论': 'has_result', '属于': 'is_a', '实例化': 'instance_of',
    '先于': 'precedes', '后于': 'follows',
    'supports': 'supports', 'contradicts': 'contradicts', 'causes': 'causes',
    'extends': 'extends', 'related_to': 'related_to', 'defines': 'defines',
    'exemplifies': 'exemplifies', 'cites': 'cites', 'part_of': 'part_of',
    'leads_to': 'leads_to', 'opposes': 'opposes', 'has_method': 'has_method',
    'has_result': 'has_result', 'is_a': 'is_a', 'instance_of': 'instance_of',
    'precedes': 'precedes', 'follows': 'follows',
}

EXTRACT_SYSTEM = """你是知识图谱构建专家。从给定文本中提取知识节点和关系，输出严格的JSON格式。

输出格式（只输出JSON，不要有其他内容）：
{
  "nodes": [
    {
      "label": "节点标签（简洁，1-10个字）",
      "type": "concept|entity|event|claim|method|result|character|paper|place|term",
      "description": "简短描述（20字以内）",
      "keywords": ["关键词1", "关键词2"],
      "aliases": ["别名1"]
    }
  ],
  "edges": [
    {
      "source": "源节点标签",
      "target": "目标节点标签",
      "relation": "supports|contradicts|causes|extends|related_to|defines|exemplifies|cites|part_of|leads_to|opposes|has_method|has_result|is_a",
      "description": "关系简述",
      "confidence": 0.85
    }
  ]
}

规则：
1. 节点标签要简洁精准，避免过长
2. 只提取文本中明确出现的知识，不推断
3. 边的source和target必须在nodes列表中
4. confidence取0.5-1.0
5. 最多提取15个节点、20条边
6. 严格输出JSON，不要markdown代码块"""


def extract_kg_from_text(user, kg_project_id, text, source_ref='',
                         caller_app='api', source_lit_id=None):
    """
    使用LLM从文本提取知识图谱节点和边
    返回 {'nodes_created': N, 'edges_created': M, 'total_nodes': N, 'total_edges': M, 'error': None}
    """
    from core.llm import chat
    from accounts.models import TokenUsage
    from .models import KGProject, KGCallLog, KGNode, KGEdge

    t0 = time.time()
    result = {
        'nodes_created': 0,
        'edges_created': 0,
        'total_nodes': 0,
        'total_edges': 0,
        'error': None,
    }

    try:
        kg = KGProject.objects.get(id=kg_project_id, user=user)
    except KGProject.DoesNotExist:
        result['error'] = '图谱不存在'
        return result

    # 截断文本（避免超token）
    text_input = text[:4000] if len(text) > 4000 else text

    messages = [{'role': 'user', 'content': f"请从以下文本提取知识图谱：\n\n{text_input}"}]

    try:
        response = chat(
            user=user,
            messages=messages,
            system=EXTRACT_SYSTEM,
            scene='knowledge_graph',
            max_tokens=2000,
        )
    except Exception as e:
        result['error'] = str(e)
        return result

    llm_tokens_in = response.get('usage', {}).get('prompt_tokens', 0)
    llm_tokens_out = response.get('usage', {}).get('completion_tokens', 0)

    content = ''
    if isinstance(response, dict):
        content = response.get('content', '') or response.get('choices', [{}])[0].get('message', {}).get('content', '')
    elif isinstance(response, str):
        content = response

    # 解析JSON
    try:
        # 清理可能的markdown代码块
        content = re.sub(r'^```json\s*', '', content.strip())
        content = re.sub(r'\s*```$', '', content.strip())
        data = json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取JSON部分
        match = re.search(r'\{[\s\S]*\}', content)
        if match:
            try:
                data = json.loads(match.group())
            except Exception:
                result['error'] = f'JSON解析失败: {content[:200]}'
                return result
        else:
            result['error'] = f'无法提取JSON: {content[:200]}'
            return result

    nodes_raw = data.get('nodes', [])
    edges_raw = data.get('edges', [])

    # 创建节点
    label_to_node = {}
    for node_data in nodes_raw:
        label = str(node_data.get('label', '')).strip()
        if not label:
            continue

        node_type = NODE_TYPE_MAP.get(node_data.get('type', 'concept'), 'concept')

        node, created = KGNode.objects.get_or_create(
            kg_project=kg,
            label=label,
            defaults={
                'node_type': node_type,
                'description': str(node_data.get('description', ''))[:200],
                'keywords': node_data.get('keywords', [])[:10],
                'aliases': node_data.get('aliases', [])[:5],
                'source_ref': source_ref,
                'source_lit_id': source_lit_id,
            }
        )

        label_to_node[label] = node
        if created:
            result['nodes_created'] += 1

    # 创建边
    for edge_data in edges_raw:
        src_label = str(edge_data.get('source', '')).strip()
        tgt_label = str(edge_data.get('target', '')).strip()
        relation = RELATION_MAP.get(edge_data.get('relation', 'related_to'), 'related_to')

        src_node = label_to_node.get(src_label)
        tgt_node = label_to_node.get(tgt_label)

        if not src_node or not tgt_node or src_node.id == tgt_node.id:
            continue

        _, created = KGEdge.objects.get_or_create(
            kg_project=kg,
            source=src_node,
            target=tgt_node,
            relation_type=relation,
            defaults={
                'confidence': float(edge_data.get('confidence', 0.8)),
                'description': str(edge_data.get('description', ''))[:200],
                'source_citation': source_ref,
            }
        )
        if created:
            result['edges_created'] += 1

    # 更新图谱计数
    kg.node_count = kg.nodes.count()
    kg.edge_count = kg.edges.count()
    kg.save(update_fields=['node_count', 'edge_count', 'updated_at'])

    result['total_nodes'] = kg.node_count
    result['total_edges'] = kg.edge_count

    duration_ms = int((time.time() - t0) * 1000)

    # 记录调用日志
    KGCallLog.record(
        user=user, kg_project=kg,
        operation='extract_text', caller_app=caller_app,
        input_length=len(text_input),
        nodes_created=result['nodes_created'],
        edges_created=result['edges_created'],
        llm_tokens_input=llm_tokens_in,
        llm_tokens_output=llm_tokens_out,
        duration_ms=duration_ms,
        memory_bytes_estimated=sys.getsizeof(content) + sys.getsizeof(text_input),
    )

    return result


def _get_sys():
    import sys
    return sys


import sys


def answer_with_kg_stream(user, kg_project_id, question, extra_context=''):
    """
    使用知识图谱回答问题（流式）
    generator: yields SSE-formatted strings
    """
    from core.llm import chat_stream
    from .traversal import keyword_search_nodes, bfs_subgraph, format_subgraph_as_text
    from .models import KGProject, KGCallLog

    t0 = time.time()

    try:
        kg = KGProject.objects.get(id=kg_project_id)
        if kg.user_id != user.id and not kg.is_shared:
            yield 'data: {"type":"error","message":"无权限"}\n\n'
            return
    except KGProject.DoesNotExist:
        yield 'data: {"type":"error","message":"图谱不存在"}\n\n'
        return

    # 检索相关子图
    seed_nodes = keyword_search_nodes(kg_project_id, question, top_k=5)
    seed_ids = [n.id for n in seed_nodes]

    if seed_ids:
        subgraph = bfs_subgraph(kg_project_id, seed_ids, max_depth=2, max_nodes=30)
        kg_context = format_subgraph_as_text(subgraph)
    else:
        kg_context = ''
        subgraph = {'nodes': [], 'edges': [], 'nodes_traversed': 0, 'edges_traversed': 0}

    # 发送检索状态
    yield f'data: {json.dumps({"type":"retrieval","nodes_found":len(seed_nodes),"context_length":len(kg_context)})}\n\n'

    system = f"""你是知识图谱智能助手。基于以下知识图谱上下文回答问题。
如果图谱中没有相关信息，明确说明"图谱中暂无此信息"。
不要编造不在图谱中的内容。

{kg_context}

{extra_context}"""

    messages = [{'role': 'user', 'content': question}]

    total_tokens_in = 0
    total_tokens_out = 0

    try:
        for chunk in chat_stream(user=user, messages=messages, system=system,
                                  scene='knowledge_graph', max_tokens=1500):
            if chunk.get('type') == 'delta':
                yield f'data: {json.dumps({"type":"chunk","text":chunk["text"]})}\n\n'
            elif chunk.get('type') == 'usage':
                total_tokens_in = chunk.get('input_tokens', 0)
                total_tokens_out = chunk.get('output_tokens', 0)
    except Exception as e:
        yield f'data: {json.dumps({"type":"error","message":str(e)})}\n\n'
        return

    duration_ms = int((time.time() - t0) * 1000)

    KGCallLog.record(
        user=user, kg_project=kg,
        operation='query_subgraph', caller_app='api',
        input_length=len(question),
        nodes_traversed=subgraph['nodes_traversed'],
        edges_traversed=subgraph['edges_traversed'],
        result_nodes=len(subgraph['nodes']),
        llm_tokens_input=total_tokens_in,
        llm_tokens_output=total_tokens_out,
        duration_ms=duration_ms,
    )

    yield f'data: {json.dumps({"type":"done","duration_ms":duration_ms})}\n\n'
