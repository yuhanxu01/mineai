import json
import re
from collections import Counter
from core.llm import chat
from core.diff_agent import edit_text_with_diff
from core.models import AgentLog
from memory.models import (
    MemoryNode, MemorySnapshot, MemoryLink, Character,
    CharacterSnapshot, CharacterRelation, TimelineEvent
)

CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

CONSOLIDATION_PROMPTS = {
    4: "提取这段文本中的关键事实、角色行为和情节要点。详细但简洁。",
    3: "总结这个场景：涉及哪些角色、发生了什么、情感基调如何、对剧情有什么意义。",
    2: "总结这一章：主要事件、角色发展、剧情推进、主题元素。",
    1: "总结这条故事线：主题走向、角色成长轨迹、重大剧情里程碑。",
    0: "提供故事的全局概览：前提设定、主要角色、核心冲突、当前叙事状态。",
}


def _log(project_id, title, content=''):
    AgentLog.objects.create(
        project_id=project_id, level='memory', title=title, content=str(content)[:1000]
    )


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) > chunk_size and current:
            chunks.append(current.strip())
            words = current.split()
            overlap_words = words[-overlap:] if len(words) > overlap else words
            current = " ".join(overlap_words) + "\n\n" + para
        else:
            current = current + "\n\n" + para if current else para
    if current.strip():
        chunks.append(current.strip())
    return chunks





def _save_snapshot(node, reason=''):
    MemorySnapshot.objects.create(
        node=node,
        version=node.version,
        summary=node.summary,
        content=node.content,
        chapter_index=node.chapter_index,
        change_reason=reason,
    )


def update_node_with_history(node, new_summary, new_content='', reason='', chapter_index=None):
    _save_snapshot(node, reason=reason or '内容更新')
    node.version += 1
    node.summary = new_summary
    if new_content:
        node.content = new_content
    if chapter_index is not None:
        node.chapter_index = chapter_index
    node.save()
    return node


def edit_node_partial(project_id, node_id, instruction):
    node = MemoryNode.objects.get(id=node_id, project_id=project_id)
    is_content = bool(node.content)
    original_text = node.content if is_content else node.summary
    
    _log(project_id, f"Agent局部编辑节点: {node.title[:50]}", instruction)
    
    new_text, applied_diffs = edit_text_with_diff(project_id, original_text, instruction)
    
    if applied_diffs:
        if is_content:
            update_node_with_history(node, new_summary=node.summary, new_content=new_text, reason=f'Agent局部修改 ({len(applied_diffs)}处)')
        else:
            update_node_with_history(node, new_summary=new_text, reason=f'Agent局部修改 ({len(applied_diffs)}处)')
            
    return node, new_text, applied_diffs


def ingest_text(project_id, text, title="", parent_id=None, node_type='narrative',
                chapter_title=None, chapter_index=0):
    _log(project_id, f"录入文本: {title or '无标题'}", f"{len(text)} 字符")

    chunks = chunk_text(text)
    _log(project_id, f"切分为 {len(chunks)} 个片段")

    scene_parent = None
    if parent_id:
        scene_parent = MemoryNode.objects.filter(id=parent_id).first()
    if not scene_parent and chapter_title:
        scene_parent = MemoryNode.objects.filter(
            project_id=project_id, level=2, title__icontains=chapter_title
        ).first()

    street_nodes = []
    for i, chunk in enumerate(chunks):
        node = MemoryNode.objects.create(
            project_id=project_id,
            parent=scene_parent,
            level=4,
            node_type=node_type,
            title=f"{title} - 片段{i+1}" if title else f"片段{i+1}",
            summary=chunk[:300],
            content=chunk,
            importance=0.5,
            chapter_index=chapter_index,
            metadata={"chunk_index": i, "total_chunks": len(chunks)}
        )
        street_nodes.append(node)

        if i > 0:
            MemoryLink.objects.create(
                project_id=project_id,
                source=street_nodes[i-1], target=node,
                link_type='temporal',
                description=f'时序片段 {i} → {i+1}'
            )

    if len(street_nodes) >= 2:
        consolidate_to_scene(project_id, street_nodes, title, scene_parent, chapter_index)

    # extract timeline events
    _extract_timeline_events(project_id, text, chapter_index)

    _log(project_id, f"录入完成: 创建了 {len(street_nodes)} 个记忆节点")
    return street_nodes


def consolidate_to_scene(project_id, street_nodes, title, parent=None, chapter_index=0):
    combined = "\n".join([n.content for n in street_nodes])
    summary = chat(
        [{"role": "user", "content": f"{CONSOLIDATION_PROMPTS[3]}\n\n文本:\n{combined[:6000]}"}],
        system="你是一个故事分析助手。用中文简洁地回应。",
        project_id=project_id
    )
    scene = MemoryNode.objects.create(
        project_id=project_id, parent=parent,
        level=3, node_type='narrative',
        title=f"场景: {title}" if title else "场景",
        summary=summary,
        importance=0.6,
        chapter_index=chapter_index,
    )
    for n in street_nodes:
        n.parent = scene
        n.save(update_fields=['parent'])
    return scene


def consolidate_chapter(project_id, chapter_node_id):
    chapter = MemoryNode.objects.get(id=chapter_node_id)
    scenes = MemoryNode.objects.filter(project_id=project_id, parent=chapter, level=3)
    if not scenes.exists():
        return chapter

    combined = "\n---\n".join([s.summary for s in scenes])
    summary = chat(
        [{"role": "user", "content": f"{CONSOLIDATION_PROMPTS[2]}\n\n场景:\n{combined[:8000]}"}],
        system="你是一个故事分析助手。用中文简洁地回应。",
        project_id=project_id
    )
    update_node_with_history(chapter, summary, reason='章节整合', chapter_index=chapter.chapter_index)
    return chapter


def consolidate_arc(project_id, arc_node_id):
    arc = MemoryNode.objects.get(id=arc_node_id)
    chapters = MemoryNode.objects.filter(project_id=project_id, parent=arc, level=2)
    if not chapters.exists():
        return arc

    combined = "\n---\n".join([c.summary for c in chapters])
    summary = chat(
        [{"role": "user", "content": f"{CONSOLIDATION_PROMPTS[1]}\n\n章节:\n{combined[:8000]}"}],
        system="你是一个故事分析助手。用中文简洁地回应。",
        project_id=project_id
    )
    update_node_with_history(arc, summary, reason='故事线整合')
    return arc


def consolidate_universe(project_id):
    universe = MemoryNode.objects.filter(project_id=project_id, level=0).first()
    arcs = MemoryNode.objects.filter(project_id=project_id, level=1)
    if not arcs.exists():
        chapters = MemoryNode.objects.filter(project_id=project_id, level=2)
        if not chapters.exists():
            return universe
        combined = "\n---\n".join([c.summary for c in chapters[:20]])
    else:
        combined = "\n---\n".join([a.summary for a in arcs])

    summary = chat(
        [{"role": "user", "content": f"{CONSOLIDATION_PROMPTS[0]}\n\n内容:\n{combined[:10000]}"}],
        system="你是一个故事分析助手。用中文简洁地回应。",
        project_id=project_id
    )

    if universe:
        update_node_with_history(universe, summary, reason='全局整合')
    else:
        universe = MemoryNode.objects.create(
            project_id=project_id, level=0, node_type='narrative',
            title='故事宇宙', summary=summary,
            importance=1.0,
        )
    return universe


def _extract_keywords(text):
    text = re.sub(r'[^\w\s]', ' ', text)
    words = [w for w in text.split() if len(w) > 1]
    return set(words)


def _calculate_score(query_keywords, target_text):
    if not query_keywords or not target_text:
        return 0.0
    target_keywords = _extract_keywords(target_text)
    if not target_keywords:
        return 0.0
    
    intersection = query_keywords.intersection(target_keywords)
    # Simple Jaccard-like or overlap metric
    # Weight score based on the overlap to simulate semantic hits
    return len(intersection) / (len(query_keywords) + 0.1)


def retrieve_context(project_id, query, max_tokens=150000, top_k_per_level=5):
    _log(project_id, "开始记忆检索", f"查询: {query[:200]}")

    query_keywords = _extract_keywords(query)
    if not query_keywords:
        return _fallback_retrieval(project_id)

    context_parts = []
    total_chars = 0
    char_limit = max_tokens * 3
    visited = set()

    universe = MemoryNode.objects.filter(project_id=project_id, level=0).first()
    if universe and universe.summary:
        context_parts.append(f"## 故事全局概览\n{universe.summary}")
        total_chars += len(universe.summary)
        visited.add(universe.id)

    characters = Character.objects.filter(project_id=project_id)[:15]
    if characters:
        block = "## 主要角色\n"
        for c in characters:
            line = f"- **{c.name}**: {c.current_state or c.description[:200]}\n"
            block += line
        context_parts.append(block)
        total_chars += len(block)

    for level in range(1, 5):
        if total_chars >= char_limit:
            break

        nodes = list(MemoryNode.objects.filter(
            project_id=project_id, level=level
        ).exclude(id__in=visited))

        if not nodes:
            continue

        scored_nodes = []
        for node in nodes:
            text_to_search = node.content if node.content else node.summary
            score = _calculate_score(query_keywords, text_to_search)
            if score > 0:
                scored_nodes.append((node, score))

        if not scored_nodes:
            continue

        ranked = sorted(scored_nodes, key=lambda x: -x[1])
        top_nodes = ranked[:top_k_per_level]

        level_name = dict(MemoryNode.LEVEL_CHOICES).get(level, f'层级{level}')
        _log(project_id, f"在{level_name}层检索到 {len(top_nodes)} 个节点",
             ", ".join([f"{n.title}({s:.2f})" for n, s in top_nodes[:3]]))

        for node, score in top_nodes:
            if total_chars >= char_limit:
                break
            visited.add(node.id)
            node.access_count += 1
            node.save(update_fields=['access_count'])

            text = node.content if node.level == 4 else node.summary
            if text:
                header = f"## [{level_name}] {node.title} (相关度: {score:.2f})"
                block = f"{header}\n{text}\n"
                context_parts.append(block)
                total_chars += len(block)

    _log(project_id, f"检索完成: {len(context_parts)} 个块, ~{total_chars} 字符")
    return "\n---\n".join(context_parts)


def retrieve_evolution_context(project_id, query, entity_name=None):
    _log(project_id, "检索演变历史", f"查询: {query[:200]}")
    parts = []

    if entity_name:
        char = Character.objects.filter(project_id=project_id, name__icontains=entity_name).first()
        if char:
            snaps = CharacterSnapshot.objects.filter(character=char).order_by('chapter_index')
            if snaps.exists():
                parts.append(f"## {char.name} 的演变历史")
                for s in snaps:
                    parts.append(
                        f"### 第{s.chapter_index}章\n"
                        f"状态: {s.state}\n"
                        f"信念: {s.beliefs}\n"
                        f"目标: {s.goals}\n"
                        f"变化: {s.change_description}"
                    )

    events = TimelineEvent.objects.filter(project_id=project_id).order_by('chapter_index')
    if entity_name:
        events = events.filter(characters_involved__contains=[entity_name])
    events = events[:30]
    if events.exists():
        parts.append("## 时间线事件")
        for e in events:
            parts.append(f"[第{e.chapter_index}章] [{e.get_event_type_display()}] {e.title}: {e.description}")

    nodes_with_history = MemoryNode.objects.filter(
        project_id=project_id, version__gt=1
    ).order_by('-version')[:10]
    if nodes_with_history:
        parts.append("## 记忆演变记录")
        for n in nodes_with_history:
            snaps = MemorySnapshot.objects.filter(node=n).order_by('version')
            for s in snaps:
                parts.append(f"[v{s.version}] {n.title}: {s.summary[:200]} ({s.change_reason})")

    return "\n---\n".join(parts)


def _fallback_retrieval(project_id, limit=20):
    nodes = MemoryNode.objects.filter(project_id=project_id).order_by('-updated_at')[:limit]
    parts = []
    for n in nodes:
        text = n.content if n.level == 4 else n.summary
        if text:
            parts.append(f"[{n.level_name}] {n.title}\n{text}")
    return "\n---\n".join(parts)


def extract_characters(project_id, text, chapter_index=0):
    prompt = """分析以下文本，提取所有出现的角色。
对于每个角色，提供:
- name: 角色的主要称呼
- description: 基于文本的简要描述
- traits: 展现出的性格特征
- state: 当前状态/处境
- beliefs: 当前信念/观点
- goals: 当前目标

仅以有效的JSON数组格式回复:
[{"name":"...","description":"...","traits":["..."],"state":"...","beliefs":"...","goals":"..."}]

文本:
""" + text[:5000]

    result = chat(
        [{"role": "user", "content": prompt}],
        system="你是角色分析专家。仅以有效JSON回复。",
        temperature=0.3, project_id=project_id
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        chars = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return []

    created = []
    for c in chars:
        name = c.get('name', '').strip()
        if not name:
            continue
        obj, was_created = Character.objects.get_or_create(
            project_id=project_id, name=name,
            defaults={
                'description': c.get('description', ''),
                'traits': c.get('traits', []),
                'current_state': c.get('state', ''),
            }
        )
        new_state = c.get('state', '')
        if not was_created:
            if c.get('description'):
                obj.description = c['description']
            if c.get('traits'):
                obj.traits = list(set(obj.traits + c.get('traits', [])))
            if new_state:
                obj.current_state = new_state
            obj.save()

        CharacterSnapshot.objects.create(
            character=obj,
            chapter_index=chapter_index,
            state=new_state or obj.current_state,
            traits=c.get('traits', obj.traits),
            beliefs=c.get('beliefs', ''),
            goals=c.get('goals', ''),
            change_description=f'第{chapter_index}章提取' if chapter_index else '初始提取',
        )
        created.append(obj)
    return created


def _extract_timeline_events(project_id, text, chapter_index=0):
    prompt = """分析以下文本，提取关键的故事事件。
对于每个事件，提供:
- event_type: plot(剧情)/character(角色变化)/relation(关系变化)/turning(转折)/foreshadow(伏笔)/reveal(揭示)
- title: 事件标题
- description: 事件描述
- characters_involved: 涉及的角色名列表
- impact: 对后续剧情的影响

仅以有效的JSON数组格式回复。如果没有重要事件，返回空数组[]。
[{"event_type":"...","title":"...","description":"...","characters_involved":["..."],"impact":"..."}]

文本:
""" + text[:5000]

    try:
        result = chat(
            [{"role": "user", "content": prompt}],
            system="你是故事分析专家。仅以有效JSON回复。",
            temperature=0.3, project_id=project_id
        )
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        events = json.loads(cleaned)
    except Exception:
        return []

    created = []
    for e in events:
        title = e.get('title', '').strip()
        if not title:
            continue
        obj = TimelineEvent.objects.create(
            project_id=project_id,
            event_type=e.get('event_type', 'plot'),
            chapter_index=chapter_index,
            title=title,
            description=e.get('description', ''),
            characters_involved=e.get('characters_involved', []),
            impact=e.get('impact', ''),
        )
        created.append(obj)

    _log(project_id, f"提取了 {len(created)} 个时间线事件")
    return created


def get_pyramid_stats(project_id):
    stats = {}
    for level, name in MemoryNode.LEVEL_CHOICES:
        stats[name] = MemoryNode.objects.filter(project_id=project_id, level=level).count()
    stats['total_nodes'] = MemoryNode.objects.filter(project_id=project_id).count()
    stats['total_links'] = MemoryLink.objects.filter(project_id=project_id).count()
    stats['total_snapshots'] = MemorySnapshot.objects.filter(node__project_id=project_id).count()
    stats['characters'] = Character.objects.filter(project_id=project_id).count()
    stats['char_snapshots'] = CharacterSnapshot.objects.filter(character__project_id=project_id).count()
    stats['timeline_events'] = TimelineEvent.objects.filter(project_id=project_id).count()
    total_content = sum(len(n.content) for n in MemoryNode.objects.filter(project_id=project_id).only('content'))
    stats['total_content_chars'] = total_content
    stats['estimated_tokens'] = total_content // 2
    return stats


def get_pyramid_tree(project_id):
    return list(MemoryNode.objects.filter(project_id=project_id).values(
        'id', 'parent_id', 'level', 'node_type', 'title', 'importance',
        'access_count', 'version', 'chapter_index', 'created_at'
    ))
