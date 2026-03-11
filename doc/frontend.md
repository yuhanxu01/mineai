# 前端模板与交互

当前前端采用模板内嵌 React（CDN），无构建步骤。

**管理端（`templates/index.html`）**
入口：`/`。
技术：React 18 + Babel Standalone（浏览器内编译）。
本地存储：`localStorage.mf_token` 保存 Token。
核心功能：登录/注册/验证码、小说项目与章节生成、记忆金字塔统计与检索、角色与时间线管理、Agent 日志查看、OCR 项目上传与处理、平台应用列表。
API 使用：集中走 `const API='/api'` 的 fetch 包装。

**阅读端（`templates/share_index.html`）**
入口：`/share/`。
核心功能：已发布小说列表、章节阅读、主题/字体切换、书评与段评、收藏与个人列表。
API 使用：`/api/share` 与 `/api/auth`。

**前端设计要点**
- 两个模板均为单文件 SPA，包含样式与脚本
- 不依赖 webpack/vite；上线时确保 CDN 可访问
- JS 代码量较大，建议后续拆分为独立前端工程

**维护建议**
- 若需要更复杂交互或性能优化，建议迁移为独立前端项目
- 若引入构建流程，请同步更新 Django 模板加载方式
