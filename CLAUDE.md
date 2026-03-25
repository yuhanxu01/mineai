# MineAI — Claude 开发指引

这是一个 Django 多 App AI 平台，前端为单文件嵌入式 React（无构建步骤）。
在执行任何修改前，先阅读本文件，它覆盖所有默认行为。

---

## 项目结构速览

```
mineai/
├── memoryforge/        # Django 配置 (settings.py, urls.py)
├── templates/
│   ├── index.html      # 主 SPA (~5700 行，React+Babel CDN)
│   └── share_index.html
├── core/               # LLM调用, Diff引擎, AgentLog
├── memory/             # 记忆金字塔 (pyramid.py, models.py)
├── accounts/           # 登录/注册/Token/用量
├── novel/              # 网文写作
├── code_agent/         # 代码助手
├── ocr_studio/         # OCR处理
├── paper_lab/          # 学术研究
├── knowledge_graph/    # 知识图谱
├── scan_enhance/       # 扫描增强
├── hub/                # 应用列表 /api/platform/
├── dashboard/          # 用户仪表板
└── claude_bridge/      # /api/bridge/
```

---

## 核心复用层（必须使用，禁止绕过）

| 功能 | 路径 | 说明 |
|------|------|------|
| LLM 调用 | `core/llm.py` `chat()` / `chat_stream()` | 所有 App 必须走这里，禁止直接调用 SDK |
| Diff 引擎 | `core/diff_agent.py` | `DIFF_SYSTEM_PROMPT`, `parse_diff_blocks`, `apply_diffs` |
| 记忆金字塔 | `memory/pyramid.py` | `retrieve_context()`, `ingest_text()` |
| Agent 日志 | `core/models.py` `AgentLog` | 所有 App 的 LLM 操作都应记录 |

---

## 添加新 App —— 标准流程

### 1. 创建 Django App
```bash
python manage.py startapp <app_name>
```

### 2. 注册（`memoryforge/settings.py` INSTALLED_APPS）
```python
'<app_name>',
```

### 3. 注册路由（`memoryforge/urls.py`）
```python
path('api/<prefix>/', include('<app_name>.urls')),
```

### 4. memory_project_id 隔离（如果用记忆金字塔）
```python
# 每个 App 使用不同偏移避免 MemoryNode.project_id 冲突
# novel:        project_id = novel_project.id          (原始，无偏移)
# code_agent:   project_id = 500000 + code_project.id
# 新 App:       project_id = 600000 + project.id  (或更大偏移)
```

### 5. 前端路由（`templates/index.html`）
搜索 `STATIC_APPS` 数组（约第 2088 行），添加应用卡片：
```js
{ id: '<slug>', name: '<显示名>', icon: '<emoji>', desc: '<描述>', route: '#/app/<slug>' }
```
搜索 `Root` 组件路由区域（约第 2570 行），添加：
```js
if (route === '#/app/<slug>') return <AppComponent />;
```

---

## 后端开发模式

### 认证（所有需保护的视图）
```python
from core.auth import _token_auth   # 返回 user 或 None
# SSE 流式端点用 @csrf_exempt + 手动鉴权
# DRF 视图用 permission_classes = [IsAuthenticated]
```

### SSE 流式响应
```python
from django.http import StreamingHttpResponse
import json

def my_stream_view(request):
    user = _token_auth(request)
    if not user:
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    def generator():
        for chunk in chat_stream(messages):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingHttpResponse(generator(), content_type='text/event-stream')
```

### URLs 文件模板
```python
from django.urls import path
from . import views

urlpatterns = [
    path('projects/', views.project_list, name='project-list'),
    path('projects/<int:pk>/', views.project_detail, name='project-detail'),
    path('stream/', views.stream_endpoint, name='stream'),
]
```

---

## 前端开发模式

### API 调用（使用已有的 fetch 包装）
```js
// GET
const data = await F('/api/<prefix>/endpoint/');
// POST
const result = await P('/api/<prefix>/endpoint/', { key: value });
// PUT
await U('/api/<prefix>/endpoint/<id>/', { key: value });
// Token 从 localStorage.mf_token 自动注入
```

### SSE 流式消费
```js
async function* streamSSE(url, body, token) {
  // 已定义在 index.html 中，直接调用
}
// 使用：
for await (const chunk of streamSSE(url, body, token)) {
  setContent(c => c + chunk.content);
}
```

### 组件结构约定
```jsx
function MyApp() {
  const { token } = useAuth();      // 全局 auth context
  const [data, setData] = React.useState([]);

  // 列表页 + 详情/编辑侧边板
  return (
    <div style={{display:'flex', height:'100vh'}}>
      <aside className="sb">...</aside>    {/* 侧边栏用 .sb */}
      <main style={{flex:1, overflow:'auto', padding:'1.5rem'}}>...</main>
    </div>
  );
}
```

### CSS 变量（必须使用，禁止硬编码颜色）
```css
--bg, --bg2, --bg3, --bg4, --bg5   /* 背景层次 */
--fg, --fg2, --fg3                  /* 文字层次 */
--gold                              /* 主题强调色 */
--danger                            /* 危险操作色 */
```

### 流式光标
```jsx
{streaming && <span style={{animation:'blink 1s infinite'}}>▌</span>}
```

---

## 数据库迁移

```bash
python manage.py makemigrations <app_name>
python manage.py migrate
```

修改 Model 后必须执行迁移，不要跳过。

---

## 常见维护任务

### 查 Bug
1. 先查 `AgentLog`（admin 或 `/api/core/logs/`）
2. 看 Django 控制台报错
3. 看浏览器 Console → Network 标签

### 添加新 LLM 功能
1. 在 App 的 `agent.py`（或 `views.py`）中调用 `core/llm.py`
2. system prompt 写在单独变量 `XXX_SYSTEM_PROMPT = "..."`
3. 流式用 `chat_stream()`，非流式用 `chat()`

### 修改前端组件
前端已拆分为多个 partial 文件，不再是单一 index.html：

| 文件 | 内容 | 约行数 |
|------|------|--------|
| `templates/index.html` | HTML骨架 + CDN + include指令 | 64 |
| `templates/partials/_styles.html` | 全局 CSS（`<style>` 块） | ~396 |
| `templates/partials/_globals.html` | F/P/U/streamSSE/useAuth/Svg/Icon 等全局工具 | ~441 |
| `templates/partials/_novel.html` | UserPanelApp + MemoryForgeApp + FloatingChat + AuthScreen + 网文写作全部组件 | ~1660 |
| `templates/partials/_settings.html` | Settings / ThemeSettings / AppColorModal / SLUG_MAP | ~295 |
| `templates/partials/_platform.html` | FeatureNavMap / PlatformHome / Root | ~656 |
| `templates/partials/_ocr.html` | OCRStudioApp + OCRUpload + OCRWork + OCRResult | ~485 |
| `templates/partials/_paper.html` | typeset + 所有学术研究组件 + PaperLabApp | ~1236 |
| `templates/partials/_kg.html` | KG常量 + 所有知识图谱组件 + KGApp | ~1209 |
| `templates/partials/_code_agent.html` | DiffBlock + FileTree + CodeAgentApp | ~922 |
| `templates/partials/_bridge.html` | TOOL_META + 所有Bridge组件 + ClaudeBridgeApp | ~1411 |
| `templates/partials/_scan.html` | CameraCapture + MeshEditor + StitchPanel + ScanEnhanceApp | ~2336 |
| `templates/partials/_qbank.html` | QBMd + QuestionBankApp + 所有QB子组件 | ~1039 |
| `templates/partials/_docreader.html` | DocReaderApp + ReactDOM.createRoot 挂载 | ~688 |

**工作流：**
1. 用 Grep 在 `templates/partials/` 下搜索组件名，确定所在文件
2. 用 Read 读取对应 partial 文件（每个文件均可完整一次读完）
3. 用 Edit 修改，改完用 preview_screenshot 验证

**每个 partial 结构：**
```
{% verbatim %}
... JSX/JS 代码 ...
{% endverbatim %}
```
Django 通过 `{% include %}` 在服务端拼接，浏览器收到的仍是一个完整 HTML。

### 部署检查
```bash
python manage.py check
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput
```

---

## 禁止事项

- 禁止直接调用 GLM/OpenAI SDK，必须走 `core/llm.py`
- 禁止硬编码颜色值，使用 CSS 变量
- 禁止在前端引入新的 npm 包或 CDN 库（除非明确讨论后决定）
- 禁止在 `memoryforge/settings.py` 写死 SECRET_KEY 或 API Key（用环境变量）
- 禁止跳过迁移直接修改数据库结构
- 不要重复造轮子：添加功能前先确认 `core/` 和 `memory/` 中是否已有

---

## 文档索引

详细说明见 `doc/` 目录：
- `doc/architecture.md` — 系统架构与流程图
- `doc/api.md` — API 端点列表
- `doc/data-models.md` — 数据模型说明
- `doc/frontend.md` — 前端模板设计
- `doc/llm-integration.md` — LLM 集成细节
- `doc/memory-system.md` — 记忆金字塔原理
- `doc/security.md` — 安全注意事项
- `doc/maintenance.md` — 维护操作手册
