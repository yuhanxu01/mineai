# API 说明

基础前缀：`/api`。鉴权采用 DRF Token（`Authorization: Token <token>`）。默认权限为 `AllowAny`，如未特别说明则为公开接口。

**Auth (`/api/auth/`)**

**POST `/api/auth/send-code/`**
- 权限：公开
- Body：`{ email }`
- 成功：`{ ok: true, cooldown_seconds }`
- 失败：`{ error, remaining_seconds? }`

**POST `/api/auth/register/`**
- 权限：公开
- Body：`{ email, password, code }`
- 成功：`{ token, email }`

**POST `/api/auth/login/`**
- 权限：公开
- Body：`{ email, password }`
- 成功：`{ token, email }`

**POST `/api/auth/logout/`**
- 权限：登录
- 成功：`{ ok: true }`

**GET `/api/auth/me/`**
- 权限：登录
- 成功：`{ authenticated, email, usage }`

**GET `/api/auth/user-api-key/`**
- 权限：登录
- 成功：`{ has_key, preview }`

**POST `/api/auth/user-api-key/`**
- 权限：登录
- Body：`{ api_key }`
- 成功：`{ ok: true, preview }`

**DELETE `/api/auth/user-api-key/`**
- 权限：登录
- 成功：`{ ok: true }`

**Core (`/api/core/`)**

**GET `/api/core/config/`**
- 权限：公开
- 返回平台或用户 API 配置状态

**POST `/api/core/config/`**
- 权限：管理员
- Body：`{ api_key, api_base?, chat_model? }`

**GET `/api/core/logs/`**
- 权限：公开
- Query：`project_id?`、`limit?`
- 返回 Agent 日志列表

**DELETE `/api/core/logs/`**
- 权限：公开
- Query：`project_id?`
- 返回：`{ deleted }`

**Memory (`/api/memory/`)**

**GET `/api/memory/{project_id}/stats/`**
- 返回记忆金字塔统计

**GET `/api/memory/{project_id}/tree/`**
- 返回 MemoryNode 简化树结构

**GET `/api/memory/{project_id}/nodes/`**
- Query：`level?`、`type?`、`limit?`
- 返回节点列表（摘要）

**GET `/api/memory/node/{node_id}/`**
- 返回节点详情、子节点、链接、快照

**DELETE `/api/memory/node/{node_id}/`**
- 删除节点

**POST `/api/memory/{project_id}/node/{node_id}/agent_edit/`**
- Body：`{ instruction }`
- 使用 diff agent 对节点局部编辑

**POST `/api/memory/{project_id}/ingest/`**
- Body：`{ text, title?, parent_id?, node_type?, chapter_index? }`
- 录入文本并构建记忆节点

**POST `/api/memory/{project_id}/consolidate/`**
- Body：`{ target: universe|arc|chapter, node_id? }`

**POST `/api/memory/{project_id}/retrieve/`**
- Body：`{ query, max_tokens? }`

**POST `/api/memory/{project_id}/retrieve-evolution/`**
- Body：`{ query, entity? }`

**GET `/api/memory/{project_id}/characters/`**
- 返回角色列表

**POST `/api/memory/{project_id}/characters/`**
- Body：`{ name, description?, traits?, aliases?, backstory?, current_state? }`

**GET `/api/memory/character/{char_id}/`**
- 返回角色详情与快照

**POST `/api/memory/{project_id}/extract-characters/`**
- Body：`{ text, chapter_index? }`

**GET `/api/memory/{project_id}/timeline/`**
- Query：`type?`

**POST `/api/memory/{project_id}/timeline/`**
- Body：`{ event_type?, chapter_index?, story_time?, title, description?, characters_involved?, impact? }`

**Novel (`/api/novel/`)**

**GET `/api/novel/projects/`**
- 权限：公开（只读）

**POST `/api/novel/projects/`**
- 权限：登录
- Body：`{ title, genre?, synopsis?, style_guide?, world_setting? }`

**GET `/api/novel/project/{project_id}/`**
- 返回项目详情与章节列表

**PUT `/api/novel/project/{project_id}/`**
- 权限：项目所有者
- Body：可更新 `title/genre/synopsis/style_guide/world_setting`

**DELETE `/api/novel/project/{project_id}/`**
- 权限：项目所有者

**POST `/api/novel/project/{project_id}/chapters/`**
- 权限：登录
- Body：`{ number?, title?, outline? }`

**GET `/api/novel/chapter/{chapter_id}/`**
- 返回章节详情

**PUT `/api/novel/chapter/{chapter_id}/`**
- 权限：项目所有者
- Body：`{ title?, outline?, content?, status? }`

**POST `/api/novel/chapter/{chapter_id}/write/`**
- 权限：登录
- Body：`{ instruction? }`

**POST `/api/novel/chapter/{chapter_id}/continue/`**
- 权限：登录
- Body：`{ instruction? }`

**POST `/api/novel/project/{project_id}/chat/`**
- 权限：登录
- Body：`{ message }`

**POST `/api/novel/project/{project_id}/outline/`**
- 权限：登录
- Body：`{ instruction? }`

**POST `/api/novel/project/{project_id}/consolidate/`**
- 权限：登录

**POST `/api/novel/generate-idea/`**
- 权限：登录
- Body：`{ title?, genre?, synopsis?, style_guide?, world_setting? }`

**Hub (`/api/platform/`)**

**GET `/api/platform/apps/`**
- 返回启用的应用列表

**Novel Share (`/api/share/`)**

**GET `/api/share/novels/`**
- 返回已发布小说（登录可见自己的草稿）

**POST `/api/share/novels/`**
- 权限：登录
- Body：`{ title, synopsis?, cover?, bg_color?, font_family?, status? }`

**GET `/api/share/novels/{id}/`**
- 返回小说详情（含章节列表）

**PUT/DELETE `/api/share/novels/{id}/`**
- 权限：作者

**GET `/api/share/novels/{novel_id}/chapters/`**
- 返回章节列表

**POST `/api/share/novels/{novel_id}/chapters/`**
- 权限：作者
- Body：`{ number, title, content }`

**GET/PUT/DELETE `/api/share/chapters/{id}/`**
- 权限：作者修改，其他只读

**GET `/api/share/novels/{novel_id}/comments/`**
- Query：`chapter_id?`、`paragraph_index?`

**POST `/api/share/novels/{novel_id}/comments/`**
- 权限：登录
- Body：`{ content, rating?, chapter_id?, paragraph_index? }`

**POST `/api/share/novels/{novel_id}/favorite/`**
- 权限：登录
- 收藏/取消收藏切换

**GET `/api/share/my-favorites/`**
- 权限：登录

**GET `/api/share/my-novels/`**
- 权限：登录

**OCR (`/api/ocr/`)**

**POST `/api/ocr/upload/`**
- 权限：登录
- Form：`file`（PDF/图片）`api_key?` `ocr_prompt?`

**POST `/api/ocr/upload-url/`**
- 权限：登录
- Body：`{ url, api_key?, ocr_prompt? }`

**GET `/api/ocr/projects/`**
- 权限：公开（只读）
- 返回所有项目列表

**GET `/api/ocr/projects/{project_id}/`**
- 权限：公开（只读）

**GET `/api/ocr/projects/{project_id}/pages/{page_num}/image/`**
- 权限：公开（只读）

**POST `/api/ocr/projects/{project_id}/ocr/`**
- 权限：登录
- Body：`{ pages, api_key?, ocr_prompt? }`

**POST `/api/ocr/projects/{project_id}/retry/{page_num}/`**
- 权限：登录

**GET `/api/ocr/projects/{project_id}/status/`**
- 权限：公开（只读）

**GET `/api/ocr/projects/{project_id}/result/`**
- 权限：公开（只读）

**GET `/api/ocr/projects/{project_id}/result/download/`**
- 权限：公开（只读）

**GET `/api/ocr/projects/{project_id}/page/{page_num}/result/`**
- 权限：公开（只读）

**DELETE `/api/ocr/projects/{project_id}/delete/`**
- 权限：登录

**前端路由（模板）**
- `/` 渲染 `templates/index.html`
- `/share/` 渲染 `templates/share_index.html`
