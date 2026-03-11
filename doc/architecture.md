# 系统架构与流程

**总体结构**
- 单体 Django 项目（`memoryforge`）+ 多个业务 app
- 前端为两个模板内嵌的 React SPA（不使用构建工具）
- 数据库默认 SQLite（`db.sqlite3`）
- 外部依赖：GLM（大模型）、OCR API

**应用分层**
- `accounts`：登录/注册、验证码、用户 API Key、Token 用量统计
- `core`：平台 API 配置、LLM 调用、Agent 日志
- `memory`：记忆金字塔、检索与角色/时间线结构化
- `novel`：小说项目与章节生成
- `novel_share`：小说发布、阅读、评论/收藏
- `ocr_studio`：OCR 上传、处理、结果输出
- `hub`：平台应用列表

**核心流程图（概览）**
```mermaid
flowchart LR
  UI[前端 SPA] -->|REST| API[Django REST API]
  API --> DB[(SQLite)]
  API --> LLM[GLM API]
  API --> OCR[OCR API]

  subgraph Apps
    ACC[accounts]
    CORE[core]
    MEM[memory]
    NOV[novel]
    SHARE[novel_share]
    OCRS[ocr_studio]
    HUB[hub]
  end

  API --> ACC
  API --> CORE
  API --> MEM
  API --> NOV
  API --> SHARE
  API --> OCRS
  API --> HUB
```

**写作与记忆流（简化）**
```mermaid
flowchart TD
  A[作者指令] --> B[novel/agent.py]
  B --> C[memory.retrieve_context]
  B --> D[memory.retrieve_evolution_context]
  C --> E[LLM 生成内容]
  E --> F[Chapter 更新]
  E --> G[memory.ingest_text]
  G --> H[MemoryNode + Snapshot]
  E --> I[extract_characters]
  I --> J[Character + TimelineEvent]
```

**OCR 流程（简化）**
```mermaid
flowchart TD
  U[上传 PDF/图片 或 URL] --> P[ocr_studio.Upload*]
  P --> S[拆页为 PNG]
  S --> DBP[OCRPage 记录]
  DBP --> O[提交 OCR 任务]
  O --> R[写入 OCR 结果]
  R --> M[合并为 Markdown]
```

**关键架构特性**
- 统一 Token 鉴权：DRF Token（`Authorization: Token <key>`）
- 用户级 API Key：允许用户自定义 LLM Key 覆盖平台配置
- 记忆系统：分层结构化存储 + 低成本检索
- OCR：本地持久化图片与结果 Markdown

**需要注意的架构点**
- 默认 `AllowAny` 权限，需依赖各 View 的权限声明
- `core.context` 基于线程局部变量，ASGI 场景需谨慎
- `db.sqlite3` 包含在仓库中，生产建议迁移至外部 DB
