# 记忆金字塔系统

**核心文件**
- `memory/models.py`
- `memory/pyramid.py`
- `memory/views.py`

**层级结构**
- 0 世界（全局概览）
- 1 大陆（主要故事线/大篇章）
- 2 王国（章节）
- 3 城池（场景）
- 4 街巷（细节片段）

**节点类型**
`narrative`、`character`、`worldbuild`、`plot`、`style`、`relation`、`foreshadow`、`setting`

**录入流程**
1. `ingest_text` 按段落切分为 `CHUNK_SIZE=800`，重叠 `CHUNK_OVERLAP=100`
2. 生成 L4 细节节点（街巷）
3. 自动建立 `temporal` 链接
4. 合并为场景节点（L3）
5. 触发时间线事件抽取

**整合流程**
- `consolidate_scene`、`consolidate_chapter`、`consolidate_arc`、`consolidate_universe`
- 调用 LLM 生成上层摘要，并保存历史快照

**检索流程**
- 基于关键词的简单打分（交集 / |query|）
- 从 L0 开始拼接上下文
- 逐层选取 top K 节点
- 记录访问次数 `access_count`

**演变检索**
- 角色快照（按章）
- 时间线事件
- 有历史版本的 MemoryNode 快照

**API 入口**
- `/api/memory/{project_id}/retrieve/` 常规检索
- `/api/memory/{project_id}/retrieve-evolution/` 演变检索
- `/api/memory/{project_id}/consolidate/` 多层整合
