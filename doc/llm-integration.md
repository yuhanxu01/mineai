# LLM / Agent 集成

**核心文件**
- `core/llm.py`：GLM API 调用封装
- `core/diff_agent.py`：局部修改（搜索/替换块）
- `novel/agent.py`：章节生成/续写/对话
- `memory/pyramid.py`：整合与抽取调用 LLM

**配置来源与优先级**
1. 如果用户已设置 `accounts.User.user_api_key`，则优先使用该 key
2. 否则使用 `core.APIConfig` 中的平台 key
3. 若都不存在，抛出错误提示用户配置

**调用路径**
- `core.llm.chat()` 构造 payload 并调用 `GLM` API
- 调用前后会写入 `core.AgentLog`
- 成功调用后，若能识别出使用量则写入 `accounts.TokenUsage`

**Diff Agent**
- 通过 `core/diff_agent.py` 约束模型输出为搜索/替换块
- `apply_diffs` 仅替换第一次出现的原文片段
- 容错：若严格匹配失败，尝试 `strip()` 版本

**关键参数**
- `api_base` 默认 `https://open.bigmodel.cn/api/paas/v4`
- `chat_model` 默认 `glm-4.7-flash`
- `max_tokens` 常见值 2048/4096/100000

**注意事项**
- API Key 存储在数据库明文字段中
- `core.context` 使用线程局部变量保存 user_id，ASGI 场景需评估线程安全
