# OCR 子系统

**核心文件**
- `ocr_studio/models.py`
- `ocr_studio/views.py`

**数据路径**
- `data/ocr/uploads/` 上传原始文件
- `data/ocr/pages/{project_id}/` 拆页图片
- `data/ocr/results/{project_id}.md` 合并后的 Markdown 结果

**主要流程**
1. 上传 PDF/图片或提供 URL
2. PDF 通过 PyMuPDF 转为 PNG 图片
3. 保存 OCRProject / OCRPage 记录
4. 选择页面提交 OCR（多线程逐页处理）
5. 结果存入 `OCRPage.ocr_result`
6. 合并生成 Markdown

**OCR API**
- URL：`https://api.z.ai/api/paas/v4/layout_parsing`
- model：`glm-ocr`
- 输入：Base64 图片
- 输出：`md_results` 或 `choices.message.content`

**注意事项**
- 当前 `ProjectsListView` 返回所有项目（未按用户过滤）
- 上传 URL 未限制域名，存在 SSRF 风险
- OCR API Key 保存在数据库明文字段
