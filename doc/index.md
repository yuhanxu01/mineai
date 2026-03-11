# 文档索引与项目目录

**文档导航**
- [README](./README.md)
- [架构](./architecture.md)
- [数据模型](./data-models.md)
- [API](./api.md)
- [前端模板](./frontend.md)
- [LLM/Agent](./llm-integration.md)
- [记忆系统](./memory-system.md)
- [OCR](./ocr.md)
- [运维](./operations.md)
- [维护](./maintenance.md)
- [安全](./security.md)
- [测试](./testing.md)

**顶层目录说明**
- `accounts/` 账号体系、验证码与用户 API Key
- `core/` 平台配置、LLM 调用与日志
- `memory/` 记忆金字塔与检索系统
- `novel/` 小说项目与章节生成
- `novel_share/` 共享小说与阅读评论
- `ocr_studio/` OCR 上传、解析与结果输出
- `hub/` 平台应用入口（应用列表）
- `templates/` 前端 SPA 模板（管理端与阅读端）
- `static/` 静态资源目录（当前为空）
- `data/` OCR 处理中间文件与结果
- `memoryforge/` Django 项目配置
- `manage.py` Django 管理入口
- `start.sh` 一键启动脚本（本地）
- `create_test_data.py` 创建测试数据脚本
- `db.sqlite3` SQLite 数据库（开发用）

**关键文件索引**
- `memoryforge/settings.py` 全局配置、应用与中间件
- `memoryforge/urls.py` 总路由
- `core/llm.py` GLM API 调用封装
- `core/diff_agent.py` LLM 文字局部修改（搜索/替换块）
- `memory/pyramid.py` 记忆系统核心逻辑
- `novel/agent.py` 章节生成与续写流程
- `ocr_studio/views.py` OCR 业务流程与文件处理
- `templates/index.html` 管理端 SPA
- `templates/share_index.html` 阅读端 SPA

**依赖提示（代码中出现的主要依赖）**
- Django, Django REST Framework, django-cors-headers
- requests, PyMuPDF(fitz), Pillow
- 其它 Python 标准库（json, urllib, threading 等）

**缺失/空白点（需注意）**
- 未发现 `requirements.txt` 或 `pyproject.toml`
- 单元测试文件多数为空
