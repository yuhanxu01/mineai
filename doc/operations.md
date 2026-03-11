# 运维与配置

**启动方式**
推荐使用脚本：`./start.sh`。脚本会清理 8000 端口、执行迁移并启动 `runserver`。
手动启动：`python manage.py migrate` 后再 `python manage.py runserver 0.0.0.0:8000`。

**配置要点（`memoryforge/settings.py`）**
- `DEBUG=True`，`ALLOWED_HOSTS=['*']`（生产需修改）
- `CORS_ALLOW_ALL_ORIGINS=True`（生产需收紧）
- 邮件配置已硬编码（应改为环境变量）
- REST 默认权限 `AllowAny`（需在 View 中显式限制）

**数据库**
默认 SQLite：`db.sqlite3`。生产建议迁移至 PostgreSQL / MySQL。

**静态文件**
`STATIC_URL='static/'`，`STATICFILES_DIRS=[BASE_DIR / 'static']`。

**依赖提示**
Django、DRF、corsheaders、requests、PyMuPDF(fitz)、Pillow。

**部署建议**
使用环境变量管理密钥与邮件配置；生产使用 `gunicorn` + `nginx` 或 ASGI 服务；增加日志收集与告警。
