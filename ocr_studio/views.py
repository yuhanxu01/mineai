"""
OCR Studio 后端 —— 纯代理层。

所有重计算（PDF 渲染、图片转换）都在浏览器端完成；
后端只负责转发 OCR API 请求，解决浏览器跨域限制。
"""
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

OCR_API_URL = 'https://api.z.ai/api/paas/v4/layout_parsing'
# 单张图片 base64 最大约 40 MB（对应原图 ~30 MB，已足够）
MAX_B64_SIZE = 40 * 1024 * 1024


class OCRRecognizeView(APIView):
    """
    浏览器端把页面渲染成 base64 PNG，POST 到这里，
    后端转发给 OCR API 并把结果原样返回。

    请求体（JSON）：
        image_b64  str   base64 编码的 PNG（不含 data: 前缀）
        api_key    str   用户自己的 OCR API 密钥
        prompt     str   可选，自定义提示词
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image_b64 = request.data.get('image_b64', '')
        api_key = request.data.get('api_key', '').strip()
        prompt = request.data.get('prompt', '').strip()

        if not image_b64:
            return Response({'error': '请提供图片数据'}, status=status.HTTP_400_BAD_REQUEST)
        if not api_key:
            return Response({'error': '请提供 API 密钥'}, status=status.HTTP_400_BAD_REQUEST)
        if len(image_b64) > MAX_B64_SIZE:
            return Response({'error': '图片过大（>30 MB），请降低分辨率后重试'},
                            status=status.HTTP_400_BAD_REQUEST)

        payload = {"model": "glm-ocr", "file": f"data:image/png;base64,{image_b64}"}
        if prompt:
            payload["prompt"] = prompt

        try:
            resp = requests.post(
                OCR_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                timeout=120,
            )
        except requests.RequestException as e:
            return Response({'error': f'网络错误: {e}'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if resp.status_code != 200:
            return Response(
                {'error': f'OCR API 错误 {resp.status_code}: {resp.text[:300]}'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        data = resp.json()
        text = (
            data.get('md_results', '')
            or data.get('data', {}).get('md_results', '')
            or data.get('data', {}).get('content', '')
            or data.get('content', '')
        )
        if not text and 'choices' in data:
            text = data['choices'][0].get('message', {}).get('content', '')

        return Response({'text': text or str(data)})
