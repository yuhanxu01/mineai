"""
scan_enhance/views.py
所有图像处理算法已迁移至前端 JavaScript (Web Worker)。
后端仅保留一个 status 端点，供前端检测运行模式。
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class StatusView(APIView):
    """返回处理模式：client-side JS，无需 OpenCV。"""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            'mode': 'client',
            'js_processing': True,
            'cv2_available': False,
            'message': '所有图像处理运行在浏览器端 Web Worker 中，无需服务器 CPU。',
        })
