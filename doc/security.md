# 安全与风险提示

**当前已识别风险**
- `settings.py` 中硬编码 `SECRET_KEY` 与邮件密码
- `DEBUG=True` 与 `ALLOWED_HOSTS=['*']`
- `CORS_ALLOW_ALL_ORIGINS=True`
- `REST_FRAMEWORK` 默认 `AllowAny`，部分接口未显式限制
- OCR 项目与结果列表为公开可读（`IsAuthenticatedOrReadOnly` + 未按用户过滤）
- `UploadURLView` 支持任意 URL 下载，存在 SSRF 风险
- API Key 明文存储（平台、用户、OCR）

**建议改进**
- 使用环境变量或秘密管理服务替代硬编码
- 默认权限改为 `IsAuthenticated`，再按需放开
- OCR 资源按用户过滤并增加鉴权
- 对 `UploadURLView` 增加白名单/域名校验与大小限制
- 对上传文件设置大小限制与类型校验
- 在生产环境关闭 `DEBUG` 并收紧 `ALLOWED_HOSTS`
