"""
学术研究 Agent
核心原则：
  - 零幻觉：只引用数据库中实际存在的文献片段，禁止推测
  - 精确引用：每个观点必须附带 file.md:L行号-行号 格式引用
  - 人工主导：Agent 是工具，不是决策者
"""
import json
import re
from core.llm import chat, chat_stream
from core import llm as _llm_module
from core.models import AgentLog
from .models import (
    ResearchProject, Literature, LiteratureChunk,
    ResearchConversation, ResearchMessage, ResearchIdea, WritingDraft
)
from .indexer import search_chunks, _extract_keywords


def _log(project_id, level, title, content=''):
    AgentLog.objects.create(
        project_id=project_id, level=level,
        title=title, content=str(content)[:1000]
    )


def _format_chunks_for_prompt(scored_chunks):
    """将检索到的文献块格式化为提示词上下文，包含精确引用"""
    parts = []
    for chunk, score in scored_chunks:
        lit = chunk.literature
        cite = chunk.get_citation()
        heading_info = f" | 章节: {chunk.heading}" if chunk.heading else ""
        parts.append(
            f"【引用: {cite}】【文献: {lit.title}】【作者: {lit.authors or '未知'}】"
            f"【年份: {lit.year or '未知'}】{heading_info}\n"
            f"{chunk.content}"
        )
    return "\n\n---\n\n".join(parts)


def _build_zero_hallucination_system(project=None):
    """构建零幻觉系统提示词"""
    proj_ctx = ""
    if project:
        proj_ctx = f"""
当前研究项目: {project.title}
研究方向: {project.domain or '未设定'}
研究问题: {project.research_questions[:300] if project.research_questions else '未设定'}
"""
    return f"""你是严格的学术研究助手。你的核心原则：

1. **零幻觉原则**：你只能引用下方【文献上下文】中实际存在的内容。禁止凭记忆或训练数据回答。如果文献库中没有相关内容，必须明确说"当前文献库中未找到相关内容"。

2. **精确引用原则**：每个具体观点、数据、结论，必须附带精确引用格式：
   `[文献标题简称:L起始行-结束行]`
   例如：根据[Smith2023:L45-60]的研究，该方法在...

3. **边界原则**：不提供文献范围之外的知识。如需补充背景，必须注明"(以下为通用背景知识，非文献引用)"。

4. **辅助原则**：你是研究辅助工具，帮助用户理解、分析、整合文献，最终判断由用户做出。
{proj_ctx}
回答格式：先给出直接回答，再列出引用来源。使用Markdown格式。"""


def research_chat(project_id, conversation_id, user_message, user_id):
    """
    研究对话（非流式）
    严格基于文献库回答，包含精确引用
    """
    project = ResearchProject.objects.filter(id=project_id).first()
    conv = ResearchConversation.objects.get(id=conversation_id)

    _log(project_id, 'think', f'[研究对话] 处理问题', user_message[:200])

    # 检索相关文献块
    scored_chunks = search_chunks(project_id, user_message, user_id, top_k=12)
    _log(project_id, 'action', f'检索到 {len(scored_chunks)} 个相关文献块')

    if not scored_chunks:
        response_text = "当前文献库中未找到与您问题相关的内容。请先导入相关文献，或换一种查询方式。"
        citations = []
    else:
        lit_context = _format_chunks_for_prompt(scored_chunks)
        system = _build_zero_hallucination_system(project)
        prompt = f"""【文献上下文】（以下是从文献库中检索到的相关片段，你只能基于这些内容回答）：

{lit_context}

【用户问题】：
{user_message}

请基于上述文献内容，给出详细、有依据的回答。每个观点必须有精确引用（格式：[文献简称:L行号-行号]）。
如文献内容不足以回答，请明确指出"文献库未涵盖此方面"。"""

        response_text = chat(
            [{"role": "user", "content": prompt}],
            system=system, temperature=0.3, max_tokens=3000,
            project_id=project_id
        )

        # 提取引用列表
        citations = _extract_citations_from_chunks(scored_chunks[:8])

    # 保存消息
    ResearchMessage.objects.create(
        conversation=conv, role='user', content=user_message
    )
    ResearchMessage.objects.create(
        conversation=conv, role='assistant',
        content=response_text, citations=citations,
        retrieval_query=user_message
    )

    _log(project_id, 'info', '研究对话完成', response_text[:200])
    return response_text, citations


def research_chat_stream(project_id, conversation_id, user_message, user_id,
                          user_id_ctx=None, config=None):
    """流式研究对话"""
    project = ResearchProject.objects.filter(id=project_id).first()
    conv = ResearchConversation.objects.get(id=conversation_id)

    _log(project_id, 'think', '[流式研究对话] 检索文献', user_message[:200])

    # 先发送检索状态
    yield f"data: {json.dumps({'type': 'retrieval_start'}, ensure_ascii=False)}\n\n"

    scored_chunks = search_chunks(project_id, user_message, user_id, top_k=12)
    _log(project_id, 'action', f'检索到 {len(scored_chunks)} 个相关文献块')

    citations = _extract_citations_from_chunks(scored_chunks[:8])
    yield f"data: {json.dumps({'type': 'citations', 'citations': citations}, ensure_ascii=False)}\n\n"

    # 保存用户消息
    ResearchMessage.objects.create(
        conversation=conv, role='user', content=user_message
    )

    if not scored_chunks:
        no_result = "当前文献库中未找到与您问题相关的内容。请先导入相关文献，或换一种查询方式。"
        yield f"data: {json.dumps({'type': 'chunk', 'text': no_result}, ensure_ascii=False)}\n\n"
        ResearchMessage.objects.create(
            conversation=conv, role='assistant',
            content=no_result, citations=[]
        )
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        return

    lit_context = _format_chunks_for_prompt(scored_chunks)
    system = _build_zero_hallucination_system(project)
    prompt = f"""【文献上下文】（以下是从文献库中检索到的相关片段，你只能基于这些内容回答）：

{lit_context}

【用户问题】：
{user_message}

请基于上述文献内容，给出详细、有依据的回答。每个观点必须有精确引用（格式：[文献简称:L行号-行号]）。
如文献内容不足以回答，请明确指出"文献库未涵盖此方面"。"""

    if config is None:
        config = _llm_module._get_config()

    full_content = []
    for chunk_text in _llm_module.chat_stream(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.3, max_tokens=3000,
        project_id=project_id, config=config, user_id=user_id_ctx,
    ):
        full_content.append(chunk_text)
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text}, ensure_ascii=False)}\n\n"

    full_response = ''.join(full_content)
    ResearchMessage.objects.create(
        conversation=conv, role='assistant',
        content=full_response, citations=citations,
        retrieval_query=user_message
    )

    # 更新检索计数
    for chunk, _ in scored_chunks[:8]:
        chunk.access_count += 1
        chunk.save(update_fields=['access_count'])

    _log(project_id, 'info', '流式研究对话完成')
    yield f"data: {json.dumps({'type': 'done', 'citations': citations}, ensure_ascii=False)}\n\n"


def _extract_citations_from_chunks(scored_chunks):
    """从检索结果构建引用列表"""
    citations = []
    seen = set()
    items = scored_chunks if isinstance(scored_chunks[0], LiteratureChunk) else [c for c, _ in scored_chunks]
    for item in items:
        if isinstance(item, tuple):
            chunk = item[0]
        else:
            chunk = item
        key = (chunk.literature_id, chunk.line_start, chunk.line_end)
        if key in seen:
            continue
        seen.add(key)
        citations.append({
            'lit_id': chunk.literature_id,
            'chunk_id': chunk.id,
            'lit_title': chunk.literature.title,
            'file_ref': chunk.literature.get_file_ref(),
            'line_start': chunk.line_start,
            'line_end': chunk.line_end,
            'cite_key': chunk.get_citation(),
            'cite_display': chunk.get_citation_display(),
            'heading': chunk.heading,
            'preview': chunk.content[:150],
        })
    return citations


def generate_ideas(project_id, user_id, focus_query="", lit_ids=None):
    """
    基于文献库生成研究灵感（必须有文献依据）
    """
    project = ResearchProject.objects.filter(id=project_id).first()
    if not project:
        return []

    query = focus_query or (project.research_questions or project.title)
    _log(project_id, 'think', '[启发] 开始检索文献寻找研究灵感', query[:200])

    scored_chunks = search_chunks(project_id, query, user_id, top_k=20, lit_ids=lit_ids)
    if not scored_chunks:
        return []

    lit_context = _format_chunks_for_prompt(scored_chunks)
    system = _build_zero_hallucination_system(project)
    prompt = f"""【文献上下文】：
{lit_context}

【任务】：基于以上文献，从中发现以下类型的研究机会（每种最多2条，仅基于文献，不要天马行空）：
- 研究空白（gap）：文献未覆盖但重要的方向
- 文献矛盾（contradiction）：不同文献间的矛盾或分歧
- 扩展方向（extension）：现有工作可以延伸的方向
- 方法创新（method）：方法改进机会

输出严格的JSON数组，每条包含：
{{
  "type": "gap|contradiction|extension|method",
  "title": "简短标题",
  "description": "描述（100-200字）",
  "evidence": "引用依据，格式：[文件:L行-行] 原文片段",
  "chunk_ids": [相关chunk的id列表]
}}

仅输出JSON，不要其他文字："""

    result = chat(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.4, max_tokens=3000,
        project_id=project_id
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        ideas_data = json.loads(cleaned)
    except Exception:
        _log(project_id, 'error', '灵感解析失败', result[:200])
        return []

    chunk_map = {c.id: c for c, _ in scored_chunks}
    created_ideas = []
    type_map = {'gap': 'gap', 'contradiction': 'contradiction',
                'extension': 'extension', 'method': 'method',
                'connection': 'connection', 'hypothesis': 'hypothesis'}

    for idea_data in ideas_data[:8]:
        idea = ResearchIdea.objects.create(
            user_id=user_id,
            project=project,
            idea_type=type_map.get(idea_data.get('type', 'gap'), 'gap'),
            title=idea_data.get('title', '未命名灵感')[:512],
            description=idea_data.get('description', ''),
            evidence_summary=idea_data.get('evidence', ''),
        )
        chunk_ids = idea_data.get('chunk_ids', [])
        valid_chunks = [chunk_map[cid] for cid in chunk_ids if cid in chunk_map]
        if valid_chunks:
            idea.evidence_chunks.set(valid_chunks)
        created_ideas.append(idea)

    _log(project_id, 'info', f'生成了 {len(created_ideas)} 条研究灵感')
    return created_ideas


def assist_writing_stream(project_id, draft_id, user_instruction, user_id,
                           section_context="", user_id_ctx=None, config=None):
    """
    写作辅助（流式）：根据文献库，为当前草稿段落提供有引用的内容建议
    """
    project = ResearchProject.objects.filter(id=project_id).first()
    draft = WritingDraft.objects.get(id=draft_id)

    query = f"{user_instruction} {section_context[:200]}"
    scored_chunks = search_chunks(project_id, query, user_id, top_k=10)
    citations = _extract_citations_from_chunks(scored_chunks[:8]) if scored_chunks else []

    yield f"data: {json.dumps({'type': 'citations', 'citations': citations}, ensure_ascii=False)}\n\n"

    if not scored_chunks:
        yield f"data: {json.dumps({'type': 'chunk', 'text': '文献库中未找到相关内容，无法提供有引用的写作建议。'}, ensure_ascii=False)}\n\n"
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
        return

    lit_context = _format_chunks_for_prompt(scored_chunks)
    system = _build_zero_hallucination_system(project)
    prompt = f"""【文献上下文】：
{lit_context}

【当前草稿段落上下文】：
{section_context[:1000] if section_context else '（无）'}

【写作指令】：{user_instruction}

请基于文献内容，为当前段落提供写作建议或内容。要求：
1. 每个论断必须有精确引用 [文献简称:L行号-行号]
2. 直接给出可使用的段落文字（Markdown格式）
3. 使用学术写作风格
4. 不要添加文献范围外的内容"""

    if config is None:
        config = _llm_module._get_config()

    full_content = []
    for chunk_text in _llm_module.chat_stream(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.3, max_tokens=2000,
        project_id=project_id, config=config, user_id=user_id_ctx,
    ):
        full_content.append(chunk_text)
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk_text}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done', 'citations': citations}, ensure_ascii=False)}\n\n"


def explore_literature(project_id, user_id, query, exploration_depth=2):
    """
    深度探索文献迷宫：从查询出发，逐层展开相关概念
    返回一个知识图谱结构
    """
    _log(project_id, 'think', '[探索] 开始文献迷宫探索', query[:200])

    # 第一层：直接检索
    layer1 = search_chunks(project_id, query, user_id, top_k=8)
    if not layer1:
        return {'nodes': [], 'edges': [], 'summary': '文献库中未找到相关内容'}

    exploration = {
        'query': query,
        'layers': [],
        'total_chunks': 0,
    }

    visited_chunk_ids = set()
    all_scored = list(layer1)

    for layer_idx in range(exploration_depth):
        layer_chunks = all_scored[layer_idx * 8:(layer_idx + 1) * 8]
        if not layer_chunks:
            break

        layer_kw = set()
        layer_data = []
        for chunk, score in layer_chunks:
            if chunk.id in visited_chunk_ids:
                continue
            visited_chunk_ids.add(chunk.id)
            layer_kw.update(chunk.keywords[:5])
            layer_data.append({
                'chunk_id': chunk.id,
                'lit_id': chunk.literature_id,
                'lit_title': chunk.literature.title,
                'cite': chunk.get_citation(),
                'score': round(score, 3),
                'heading': chunk.heading,
                'preview': chunk.content[:200],
            })

        exploration['layers'].append({
            'depth': layer_idx + 1,
            'chunks': layer_data,
        })
        exploration['total_chunks'] += len(layer_data)

        # 第二层扩展：基于提取的关键词继续搜索
        if layer_idx < exploration_depth - 1 and layer_kw:
            expand_query = ' '.join(list(layer_kw)[:10])
            next_chunks = search_chunks(project_id, expand_query, user_id, top_k=8)
            new_chunks = [(c, s) for c, s in next_chunks if c.id not in visited_chunk_ids]
            all_scored.extend(new_chunks)

    # 生成探索摘要
    if all_scored:
        context = _format_chunks_for_prompt(all_scored[:10])
        project = ResearchProject.objects.filter(id=project_id).first()
        summary = chat(
            [{"role": "user", "content": f"基于以下文献片段，用200字总结关于'{query}'的核心发现，每个要点必须引用：\n\n{context}"}],
            system=_build_zero_hallucination_system(project),
            temperature=0.3, max_tokens=500, project_id=project_id
        )
        exploration['summary'] = summary
        exploration['all_citations'] = _extract_citations_from_chunks(all_scored[:15])

    _log(project_id, 'info', f'探索完成，覆盖 {exploration["total_chunks"]} 个文献块')
    return exploration


def analyze_literature_structure(lit_id, project_id):
    """分析单篇文献的结构：提取章节、关键概念、主要论点"""
    lit = Literature.objects.get(id=lit_id)
    chunks = LiteratureChunk.objects.filter(literature=lit).order_by('chunk_index')

    headings = list(chunks.filter(heading__isnull=False).values_list('heading', flat=True).distinct())
    headings = [h for h in headings if h]

    # 取摘要块 + 部分内容块做分析
    abstract_chunks = chunks.filter(chunk_type='abstract')
    sample_chunks = list(abstract_chunks) + list(chunks[:5])
    context = "\n\n".join([c.content for c in sample_chunks[:6]])

    if not context:
        return {"error": "文献内容为空"}

    result = chat(
        [{"role": "user", "content": f"""分析以下文献片段，提取：
1. 主要研究问题
2. 核心方法
3. 主要结论
4. 关键概念（5-10个）

文献标题：{lit.title}
文献内容（部分）：
{context[:3000]}

以JSON格式输出：{{"research_question":"...","methods":"...","conclusions":"...","key_concepts":["..."]}}"""}],
        system="你是学术文献分析专家。仅基于提供的文本输出JSON。",
        temperature=0.2, max_tokens=1000, project_id=project_id
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        analysis = json.loads(cleaned)
    except Exception:
        analysis = {"raw": result}

    analysis['headings'] = headings[:20]
    analysis['total_chunks'] = chunks.count()
    analysis['total_lines'] = lit.total_lines
    return analysis
