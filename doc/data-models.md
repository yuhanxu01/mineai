# 数据模型

以下为当前模型与关系的整理，字段名与约束来自 `models.py` 与迁移文件。

**accounts**

**User**
字段：`email`(唯一), `is_active`, `is_staff`, `created_at`, `user_api_key`。
认证字段：`USERNAME_FIELD = email`。

**TokenUsage**
关系：`user` OneToOne。
字段：`prompt_count`, `input_tokens`, `output_tokens`, `total_tokens`, `updated_at`。

**SiteConfig**
全局验证码策略单例（`pk=1`）。字段：`code_cooldown_seconds`, `code_expire_minutes`, `code_daily_limit`, `code_minute_limit`, `updated_at`。

**VerificationCode**
字段：`email`, `code`, `is_used`, `created_at`。索引：`email`, `created_at`。

**core**

**APIConfig**
平台 LLM 配置：`api_key`, `api_base`, `chat_model`。按 `updated_at` 排序，`get_active()` 返回第一条。

**AgentLog**
字段：`project_id`, `level`, `title`, `content`, `metadata`, `created_at`。按 `created_at` 倒序。

**novel**

**Project**
字段：`title`, `genre`, `synopsis`, `style_guide`, `world_setting`, `metadata`。
关系：`user` 外键（可为空）。

**Chapter**
字段：`number`, `title`, `outline`, `content`, `word_count`, `memory_node_id`, `status`。
关系：`project` 外键。
约束：`unique_together(project, number)`。

**memory**

**MemoryNode**
层级：0-4（世界/大陆/王国/城池/街巷）。
字段：`project_id`, `parent`, `level`, `node_type`, `title`, `summary`, `content`, `importance`, `access_count`, `version`, `story_time`, `chapter_index`, `metadata`。
索引：`(project_id, level)`, `(project_id, node_type)`, `(project_id, chapter_index)`。

**MemorySnapshot**
字段：`version`, `summary`, `content`, `chapter_index`, `change_reason`, `created_at`。
关系：`node` 外键。
约束：`unique_together(node, version)`。

**MemoryLink**
字段：`link_type`, `weight`, `description`。
关系：`source`, `target` 外键。
约束：`unique_together(source, target, link_type)`。

**Character**
字段：`name`, `aliases`, `description`, `traits`, `backstory`, `current_state`, `metadata`。
约束：`unique_together(project_id, name)`。

**CharacterSnapshot**
字段：`chapter_index`, `state`, `traits`, `beliefs`, `goals`, `relationships`, `change_description`。
关系：`character` 外键。

**CharacterRelation**
字段：`relation_type`, `description`, `evolution`。
关系：`char_a`, `char_b` 外键。
约束：`unique_together(char_a, char_b)`。

**TimelineEvent**
字段：`event_type`, `chapter_index`, `story_time`, `title`, `description`, `characters_involved`, `impact`。
关系：`memory_node` 可为空。
索引：`(project_id, chapter_index)`, `(project_id, event_type)`。

**novel_share**

**SharedNovel**
字段：`title`, `synopsis`, `cover`, `bg_color`, `font_family`, `status`, `created_at`, `updated_at`。
关系：`author` 外键。

**SharedChapter**
字段：`number`, `title`, `content`, `word_count`。
关系：`novel` 外键。
约束：`unique_together(novel, number)`。

**NovelComment**
字段：`content`, `rating`, `paragraph_index`, `created_at`。
关系：`user`, `novel`, `chapter`(可空) 外键。

**NovelFavorite**
关系：`user`, `novel` 外键。
约束：`unique_together(user, novel)`。

**hub**

**App**
字段：`name`, `slug`(唯一), `description`, `icon`, `color`, `is_active`, `order`。

**ocr_studio**

**OCRProject**
主键：`id`(12位字符串)。
字段：`name`, `total_pages`, `api_key`, `ocr_prompt`, `status`, `created_at`。
关系：`user` 外键（可空）。

**OCRPage**
字段：`page_num`, `image_path`, `ocr_status`, `ocr_result`, `error_msg`, `submitted_at`, `completed_at`。
关系：`project` 外键。
约束：`unique_together(project, page_num)`。
