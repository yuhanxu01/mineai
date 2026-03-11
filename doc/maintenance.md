# 维护手册

**常见维护操作**
- 数据库迁移：`python manage.py migrate`
- 创建管理员：`python manage.py createsuperuser`
- 清理 AgentLog：调用 `DELETE /api/core/logs/`
- 更新平台 LLM Key：`POST /api/core/config/`（管理员）
- 用户自定义 Key：`POST /api/auth/user-api-key/`
- 调整验证码频控：后台 `SiteConfig` 单例
- 清理 OCR 数据目录：`data/ocr/pages/`、`data/ocr/results/`

**监控建议**
- 监控 OCR 任务处理时间与失败率
- 监控 LLM 调用失败与 Token 使用量

**备份建议**
- SQLite：定期备份 `db.sqlite3`
- OCR 文件：可视业务需要保留或归档

**开发数据**
- `create_test_data.py` 可生成示例共享小说数据
