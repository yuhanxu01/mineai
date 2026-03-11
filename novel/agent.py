import json
from core.llm import chat
from core.models import AgentLog
from memory.pyramid import (
    retrieve_context, retrieve_evolution_context, ingest_text,
    extract_characters, consolidate_universe
)
from memory.models import MemoryNode, Character, CharacterSnapshot, TimelineEvent
from novel.models import Project, Chapter


def _log(project_id, level, title, content=''):
    AgentLog.objects.create(project_id=project_id, level=level, title=title, content=content[:1000])


def write_chapter(project_id, chapter_id, user_instruction=""):
    project = Project.objects.get(id=project_id)
    chapter = Chapter.objects.get(id=chapter_id, project=project)

    _log(project_id, 'think', f'开始撰写 第{chapter.number}章: {chapter.title}')

    query = _build_retrieval_query(project, chapter, user_instruction)

    _log(project_id, 'action', '在记忆金字塔中检索相关上下文')
    memory_context = retrieve_context(project_id, query, max_tokens=100000)

    _log(project_id, 'action', '检索角色演变历史')
    evolution_context = retrieve_evolution_context(project_id, query)

    _log(project_id, 'action', '组装上下文窗口，准备生成')
    system_prompt = _build_system_prompt(project)
    writing_prompt = _build_writing_prompt(project, chapter, memory_context, evolution_context, user_instruction)

    _log(project_id, 'action', f'调用LLM生成章节内容')
    content = chat(
        [{"role": "user", "content": writing_prompt}],
        system=system_prompt, temperature=0.8, max_tokens=4096, project_id=project_id
    )

    chapter.content = (chapter.content + "\n\n" + content).strip() if chapter.content else content
    chapter.status = 'draft'
    chapter.save()

    _log(project_id, 'action', '将新内容索引到记忆金字塔')
    ingest_text(
        project_id, content,
        title=f"第{chapter.number}章: {chapter.title}",
        parent_id=chapter.memory_node_id,
        node_type='narrative',
        chapter_index=chapter.number,
    )

    _log(project_id, 'action', '提取角色信息和时间线事件')
    try:
        extract_characters(project_id, content, chapter_index=chapter.number)
    except Exception as e:
        _log(project_id, 'error', f'角色提取失败: {str(e)}')

    _log(project_id, 'info', f'第{chapter.number}章撰写完成', f'生成了 {len(content)} 字符')
    return content


def continue_writing(project_id, chapter_id, user_instruction=""):
    project = Project.objects.get(id=project_id)
    chapter = Chapter.objects.get(id=chapter_id, project=project)

    _log(project_id, 'think', f'续写 第{chapter.number}章: {chapter.title}')

    last_paragraph = ""
    if chapter.content:
        paragraphs = chapter.content.strip().split('\n\n')
        last_paragraph = "\n\n".join(paragraphs[-3:])

    query = f"续写: {last_paragraph[:500]}"
    if user_instruction:
        query = f"{user_instruction}\n\n上文: {last_paragraph[:300]}"

    memory_context = retrieve_context(project_id, query, max_tokens=80000)
    evolution_context = retrieve_evolution_context(project_id, query)

    system_prompt = _build_system_prompt(project)
    prompt = f"""续写这一章。从文本结束处无缝衔接。
保持相同的叙事声音、语调和情节线索。

{f'作者指示: {user_instruction}' if user_instruction else ''}

## 故事上下文 (来自记忆金字塔)
{memory_context[:30000]}

## 角色与情节演变
{evolution_context[:5000]}

## 当前章节内容 (末尾部分)
{last_paragraph}

## 续写要求
从上文结束处无缝继续叙事。至少写800字的优质文学内容。"""

    content = chat(
        [{"role": "user", "content": prompt}],
        system=system_prompt, temperature=0.8, max_tokens=4096, project_id=project_id
    )

    chapter.content = (chapter.content + "\n\n" + content).strip()
    chapter.save()

    ingest_text(project_id, content, title=f"第{chapter.number}章 续写",
                parent_id=chapter.memory_node_id, chapter_index=chapter.number)
    try:
        extract_characters(project_id, content, chapter_index=chapter.number)
    except Exception:
        pass

    return content


def chat_with_agent(project_id, message):
    project = Project.objects.get(id=project_id)
    _log(project_id, 'think', '处理作者提问', message[:200])

    memory_context = retrieve_context(project_id, message, max_tokens=50000)
    evolution_context = retrieve_evolution_context(project_id, message)
    characters = Character.objects.filter(project_id=project_id)[:20]

    char_info = ""
    if characters:
        char_info = "\n## 角色列表\n" + "\n".join(
            [f"- {c.name}: {c.current_state or c.description[:150]}" for c in characters]
        )

    system = f"""你是AI写作助手，正在协助创作小说《{project.title}》。
类型: {project.genre}
简介: {project.synopsis[:500]}

你可以访问这个故事的完整记忆系统，包括情节演变历史、角色状态变化、时间线事件。
使用这些信息精确回答关于剧情、角色、世界观的问题，并辅助创作决策。
引用具体的故事内容，展示你对剧情发展脉络的掌握。
{char_info}"""

    prompt = f"""## 相关记忆上下文
{memory_context[:20000]}

## 演变历史
{evolution_context[:5000]}

## 作者的问题
{message}

请详细回答，引用具体的故事元素和演变过程。"""

    response = chat(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.7, max_tokens=2048, project_id=project_id
    )
    _log(project_id, 'info', 'Agent回答完成', response[:200])
    return response


def generate_outline(project_id, user_instruction=""):
    project = Project.objects.get(id=project_id)
    _log(project_id, 'think', '生成章节大纲')

    existing_chapters = Chapter.objects.filter(project=project)
    existing_info = ""
    if existing_chapters.exists():
        existing_info = "\n## 已有章节\n" + "\n".join(
            [f"- 第{c.number}章: {c.title} ({c.get_status_display()})" for c in existing_chapters]
        )

    prompt = f"""为这部小说生成详细的章节大纲。

标题: {project.title}
类型: {project.genre}
简介: {project.synopsis}
世界设定: {project.world_setting[:1000]}
{existing_info}

{f'作者要求: {user_instruction}' if user_instruction else ''}

生成10-20章的大纲。对于每章提供:
- number: 章节号
- title: 章节标题
- outline: 2-3句的情节描述

仅以有效JSON数组格式回复:
[{{"number": 1, "title": "...", "outline": "..."}}]"""

    result = chat(
        [{"role": "user", "content": prompt}],
        system="你是网络小说策划专家。仅以有效JSON回复。",
        temperature=0.7, max_tokens=4096, project_id=project_id
    )

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
        chapters_data = json.loads(cleaned)
    except (json.JSONDecodeError, IndexError):
        return result

    created = []
    for ch in chapters_data:
        obj, _ = Chapter.objects.update_or_create(
            project=project, number=ch['number'],
            defaults={
                'title': ch.get('title', f'第{ch["number"]}章'),
                'outline': ch.get('outline', ''),
                'status': 'outline',
            }
        )
        mem_node = MemoryNode.objects.create(
            project_id=project_id, level=2, node_type='narrative',
            title=f"第{ch['number']}章: {ch.get('title', '')}",
            summary=ch.get('outline', ''), importance=0.7,
            chapter_index=ch['number'],
        )
        obj.memory_node_id = mem_node.id
        obj.save()
        created.append(obj)

    _log(project_id, 'info', f'生成了包含 {len(created)} 章的大纲')
    return created


def _build_retrieval_query(project, chapter, user_instruction):
    parts = [chapter.title, chapter.outline]
    if user_instruction:
        parts.append(user_instruction)
    prev = Chapter.objects.filter(project=project, number=chapter.number - 1).first()
    if prev and prev.content:
        parts.append(prev.content[-500:])
    return " ".join(filter(None, parts))


def _build_system_prompt(project):
    return f"""你是一位才华横溢的网络小说家，正在创作《{project.title}》。
类型: {project.genre}
风格指导: {project.style_guide or '用引人入胜的叙事风格写作，适合中文网络小说读者。'}

写出生动、吸引人的文字。保持角色性格和情节的一致性。
用丰富的感官细节和情感深度来展现场景（而非平淡叙述）。
注意利用伏笔和前后呼应来增强故事的连贯性。
你可以看到角色的演变历史——确保他们的行为与当前的信念和状态保持一致。"""


def _build_writing_prompt(project, chapter, memory_context, evolution_context, user_instruction):
    prev_chapter = Chapter.objects.filter(project=project, number=chapter.number - 1).first()
    prev_summary = ""
    if prev_chapter:
        prev_summary = f"\n## 上一章 ({prev_chapter.title})\n"
        if prev_chapter.content:
            prev_summary += prev_chapter.content[-1000:]

    return f"""撰写 第{chapter.number}章: "{chapter.title}"

## 章节大纲
{chapter.outline}

{f'## 作者指示{chr(10)}{user_instruction}' if user_instruction else ''}

## 故事上下文 (来自记忆金字塔检索)
{memory_context[:40000]}

## 角色与情节演变历史
{evolution_context[:8000]}
{prev_summary}

## 写作要求
完整写出这一章。创建引人入胜的场景，包含对话、动作和内心活动。
确保与已建立的角色和情节线索保持连续性。
注意角色的信念和目标在前面章节中的变化——让他们的行为体现这种成长。
至少写1000字的高质量文学内容。"""
