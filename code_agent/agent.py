"""
代码助手 Agent
=============
核心设计原则：
  - 后端复用：直接使用 core/llm.py (chat/chat_stream) 和 core/diff_agent.py
  - 记忆复用：通过 memory_project_id (offset 500000) 接入 memory/pyramid.py，
              实现跨文件的代码库级长期记忆，与网文/学术写作共享同一套记忆基础设施
  - Diff工作流：与 novel/agent.py 一致的 <<<< ==== >>>> 格式，
               前端可通用 DiffViewer 组件显示和接受/拒绝每处修改
"""
import json
from core.llm import chat
from core import llm as _llm_module
from core.diff_agent import DIFF_SYSTEM_PROMPT, parse_diff_blocks, apply_diffs
from core.models import AgentLog
from memory.pyramid import retrieve_context, ingest_text, consolidate_universe


# ──────────────────────────────────────────────
# 代码领域专用记忆整合提示词
# 替换 memory/pyramid.py 的 CONSOLIDATION_PROMPTS（叙事小说版），
# 但底层 retrieve_context / ingest_text 函数完全复用，无需修改。
# ──────────────────────────────────────────────
CODE_CONSOLIDATION_PROMPTS = {
    4: "提取这段代码的关键逻辑：函数签名、主要职责、输入输出、依赖关系。简洁但完整。",
    3: "总结这个代码文件或模块：功能定位、核心类/函数列表、对外接口、与其他模块的关系。",
    2: "总结这个子目录或功能模块：包含哪些文件、整体架构职责、数据流向。",
    1: "总结这个项目层（lib/src/tests等）：主要组件、设计模式、技术选型。",
    0: "提供整个代码库的全局概览：项目目的、整体架构、主要模块、技术栈、入口点。",
}


def _log(project_id, level, title, content=''):
    AgentLog.objects.create(
        project_id=project_id, level=level,
        title=title, content=str(content)[:1000]
    )


def _detect_language(path: str) -> str:
    ext_map = {
        '.py': 'python', '.js': 'javascript', '.ts': 'typescript',
        '.tsx': 'tsx', '.jsx': 'jsx', '.java': 'java', '.go': 'go',
        '.rs': 'rust', '.cpp': 'cpp', '.c': 'c', '.cs': 'csharp',
        '.rb': 'ruby', '.php': 'php', '.swift': 'swift', '.kt': 'kotlin',
        '.sh': 'bash', '.yml': 'yaml', '.yaml': 'yaml', '.json': 'json',
        '.html': 'html', '.css': 'css', '.sql': 'sql', '.md': 'markdown',
    }
    import os
    _, ext = os.path.splitext(path.lower())
    return ext_map.get(ext, 'text')


# ──────────────────────────────────────────────
# 记忆索引：将代码文件录入记忆金字塔
# 复用 memory.pyramid.ingest_text，完全不修改
# ──────────────────────────────────────────────
def index_file(memory_project_id: int, file_path: str, content: str, language: str = ''):
    """
    将一个代码文件索引到记忆金字塔（Level 4 chunks）。
    memory_project_id = CodeProject.memory_project_id = 500000 + code_project.id
    这样与小说项目的 project_id 完全隔离，共享同一张 MemoryNode 表。
    """
    if not content.strip():
        return []
    _log(memory_project_id, 'memory', f'索引代码文件: {file_path}', f'{len(content)} 字符')
    nodes = ingest_text(
        project_id=memory_project_id,
        text=content,
        title=file_path,
        node_type='narrative',   # 复用现有 type，用 title 区分
        chapter_title=file_path,
    )
    return nodes


def index_project_files(memory_project_id: int, files):
    """
    批量索引整个项目的文件列表。
    files: iterable of CodeFile model instances
    """
    indexed = 0
    for f in files:
        if f.content and len(f.content.strip()) > 10:
            index_file(memory_project_id, f.path, f.content, f.language)
            indexed += 1
    _log(memory_project_id, 'memory', f'项目索引完成：共索引 {indexed} 个文件')
    return indexed


# ──────────────────────────────────────────────
# 代码系统提示词构造
# ──────────────────────────────────────────────
def _build_code_system(project_name: str, language: str = '') -> str:
    lang_hint = f"\n主要语言/技术栈: {language}" if language else ""
    return f"""你是专业的代码助手，正在协助开发项目《{project_name}》。{lang_hint}

你可以访问这个代码库的完整记忆系统，包含所有已索引文件的摘要和代码片段。
在回答代码问题时，始终基于记忆上下文中的实际代码，确保建议的一致性。
当提出修改建议时，使用严格的 search/replace 差异格式（<<<< ==== >>>>），确保用户可以精确审查每处变更。"""


# ──────────────────────────────────────────────
# 核心能力 1：代码对话（流式）
# 复用 core.llm.chat_stream，通过 memory.pyramid.retrieve_context 注入上下文
# ──────────────────────────────────────────────
def code_chat_stream(memory_project_id: int, project_name: str, language: str,
                     session_id: int, messages: list, current_file_path: str = '',
                     current_file_content: str = '', user_id=None, config=None):
    """
    代码对话（流式 SSE）。
    - 通过 retrieve_context 从记忆金字塔检索相关代码上下文
    - 如果打开了某个文件，将当前文件内容也注入上下文
    - 完全复用 core.llm.chat_stream，与 novel/agent.py 模式一致
    """
    from code_agent.models import CodeMessage, CodeSession

    user_message = messages[-1]['content'] if messages else ''
    _log(memory_project_id, 'think', f'[代码对话] 处理问题', user_message[:200])

    # 1. 从记忆金字塔检索相关代码上下文
    memory_context = retrieve_context(memory_project_id, user_message, max_tokens=60000)
    _log(memory_project_id, 'memory', '检索到代码记忆上下文')

    # 2. 构造提示词：记忆上下文 + 当前文件 + 对话历史
    current_file_block = ""
    if current_file_path and current_file_content:
        lang = _detect_language(current_file_path)
        current_file_block = f"""
## 当前打开的文件: {current_file_path}
```{lang}
{current_file_content[:8000]}
```
"""

    system = _build_code_system(project_name, language)

    # 将记忆上下文和文件注入为第一条系统上下文消息
    context_injection = f"""## 代码库记忆上下文（来自记忆金字塔）
{memory_context[:20000]}
{current_file_block}
"""
    # 在对话历史前面插入上下文
    full_messages = [{"role": "user", "content": context_injection},
                     {"role": "assistant", "content": "好的，我已了解当前代码库上下文，请提问。"}]
    full_messages.extend(messages)

    if config is None:
        config = _llm_module._get_config()

    _log(memory_project_id, 'action', '调用LLM进行代码对话')
    full_content = []
    for chunk in _llm_module.chat_stream(
        full_messages, system=system, temperature=0.5, max_tokens=3000,
        project_id=memory_project_id, config=config, user_id=user_id,
    ):
        full_content.append(chunk)
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

    response = ''.join(full_content)

    # 保存消息记录
    try:
        session = CodeSession.objects.get(id=session_id)
        CodeMessage.objects.create(session=session, role='assistant', content=response)
    except Exception:
        pass

    _log(memory_project_id, 'info', '代码对话完成', response[:200])
    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"


# ──────────────────────────────────────────────
# 核心能力 2：代码编辑建议（流式 Diff）
# 复用 core.diff_agent.DIFF_SYSTEM_PROMPT + parse_diff_blocks
# 与 memory.pyramid.retrieve_context 结合，让 Agent 了解全局上下文再修改局部
# ──────────────────────────────────────────────
def suggest_edits_stream(memory_project_id: int, project_name: str, language: str,
                         file_path: str, file_content: str, instruction: str,
                         user_id=None, config=None):
    """
    针对单个文件提出编辑建议（流式 SSE）。
    返回 diff 块，前端展示 accept/reject UI，与小说润色 refine_text_stream 模式完全一致。

    核心复用：
      - core/diff_agent.py 的 DIFF_SYSTEM_PROMPT（语言无关，适配代码）
      - memory/pyramid.py 的 retrieve_context（提供项目级上下文）
      - core/llm.py 的 chat_stream（统一的流式调用）
    """
    _log(memory_project_id, 'think', f'[编辑建议] {file_path}', instruction[:200])

    # 从记忆金字塔检索与此指令相关的代码上下文（跨文件感知）
    query = f"{instruction}\n\n文件: {file_path}"
    memory_context = retrieve_context(memory_project_id, query, max_tokens=30000)
    _log(memory_project_id, 'memory', '检索跨文件代码上下文')

    lang = _detect_language(file_path) or language

    # 在 DIFF_SYSTEM_PROMPT 基础上追加代码专属约束
    code_diff_system = DIFF_SYSTEM_PROMPT + f"""

补充规则（代码专用）：
- 严格保留原有缩进和换行风格
- 修改时保持语言 {lang} 的语法正确性
- 不要修改不相关的代码，保持最小变更原则
- 如需添加 import/依赖，将其作为单独的替换块"""

    prompt = f"""## 项目代码库上下文（来自记忆金字塔，了解跨文件依赖）
{memory_context[:10000]}

## 当前文件: {file_path}
```{lang}
{file_content}
```

## 修改要求
{instruction}

请使用带有 <<<< 和 ==== 和 >>>> 的搜索/替换块精确输出修改内容。"""

    if config is None:
        config = _llm_module._get_config()

    _log(memory_project_id, 'action', '调用LLM生成代码编辑建议')
    full_content = []
    for chunk in _llm_module.chat_stream(
        [{"role": "user", "content": prompt}],
        system=code_diff_system, temperature=0.3, max_tokens=4096,
        project_id=memory_project_id, config=config, user_id=user_id,
    ):
        full_content.append(chunk)
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

    raw_response = ''.join(full_content)

    # 解析 diff 块，供前端展示 accept/reject
    diffs = parse_diff_blocks(raw_response)
    _log(memory_project_id, 'info', f'生成了 {len(diffs)} 处代码修改建议')

    yield f"data: {json.dumps({'type': 'diffs', 'diffs': diffs}, ensure_ascii=False)}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'diff_count': len(diffs)}, ensure_ascii=False)}\n\n"


# ──────────────────────────────────────────────
# 核心能力 3：确认并应用 Diff
# 复用 core.diff_agent.apply_diffs
# ──────────────────────────────────────────────
def apply_confirmed_diffs(memory_project_id: int, file_path: str,
                           original_content: str, accepted_diffs: list) -> tuple:
    """
    将用户接受的 diff 应用到文件内容。
    复用 core/diff_agent.py 的 apply_diffs，完全语言无关。
    返回 (new_content, actually_applied_diffs)
    """
    new_content, applied = apply_diffs(original_content, accepted_diffs)
    _log(memory_project_id, 'action',
         f'应用 {len(applied)}/{len(accepted_diffs)} 处修改 → {file_path}')
    return new_content, applied


# ──────────────────────────────────────────────
# 核心能力 4：代码解释（非流式，用于快速查询）
# ──────────────────────────────────────────────
def explain_code(memory_project_id: int, project_name: str, language: str,
                 file_path: str, selected_code: str, question: str = '') -> str:
    """
    解释选中的代码片段，结合记忆中的跨文件上下文。
    """
    query = f"{selected_code[:300]} {question}"
    memory_context = retrieve_context(memory_project_id, query, max_tokens=20000)
    lang = _detect_language(file_path) or language

    system = _build_code_system(project_name, language)
    prompt = f"""## 项目上下文
{memory_context[:8000]}

## 需要解释的代码（来自 {file_path}）
```{lang}
{selected_code[:3000]}
```

{f'## 问题{chr(10)}{question}' if question else '请详细解释以上代码的功能、逻辑和关键点。'}

用中文回答，结合项目上下文给出准确解释。"""

    response = chat(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.4, max_tokens=2000,
        project_id=memory_project_id
    )
    _log(memory_project_id, 'info', '代码解释完成', response[:200])
    return response


# ──────────────────────────────────────────────
# 核心能力 5：项目概览生成
# 复用 memory.pyramid.consolidate_universe（与小说版完全一致）
# ──────────────────────────────────────────────
def analyze_project(memory_project_id: int, project_name: str) -> str:
    """
    整合记忆金字塔，生成项目全局概览。
    直接复用 memory.pyramid.consolidate_universe，
    与小说项目的"故事宇宙整合"使用同一套机制。
    """
    _log(memory_project_id, 'think', '整合代码库记忆，生成项目概览')
    node = consolidate_universe(memory_project_id)
    if node:
        return node.summary
    return "暂无足够代码索引，请先上传并索引项目文件。"


# ──────────────────────────────────────────────
# 核心能力 6：生成代码（新文件或新函数，流式）
# ──────────────────────────────────────────────
def generate_code_stream(memory_project_id: int, project_name: str, language: str,
                          instruction: str, context_hint: str = '',
                          user_id=None, config=None):
    """
    根据需求生成新代码（新函数、新模块等），流式返回。
    结合记忆上下文确保与现有代码风格一致。
    """
    query = f"{instruction} {context_hint}"
    memory_context = retrieve_context(memory_project_id, query, max_tokens=30000)

    system = _build_code_system(project_name, language)
    prompt = f"""## 现有代码库上下文
{memory_context[:15000]}

## 生成需求
{instruction}

{f'## 额外背景{chr(10)}{context_hint}' if context_hint else ''}

请生成符合现有代码风格和架构的代码。用代码块格式输出，并简要说明设计思路。"""

    if config is None:
        config = _llm_module._get_config()

    _log(memory_project_id, 'action', '生成新代码', instruction[:200])
    for chunk in _llm_module.chat_stream(
        [{"role": "user", "content": prompt}],
        system=system, temperature=0.5, max_tokens=4096,
        project_id=memory_project_id, config=config, user_id=user_id,
    ):
        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
