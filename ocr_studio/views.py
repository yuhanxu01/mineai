import os
import uuid
import base64
import shutil
from pathlib import Path
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.http import FileResponse
from urllib.parse import urlparse
import requests
import fitz  # PyMuPDF
from PIL import Image
from io import BytesIO

from .models import OCRProject, OCRPage


# 配置存储路径
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data' / 'ocr'
UPLOADS_DIR = DATA_DIR / 'uploads'
PAGES_DIR = DATA_DIR / 'pages'
RESULTS_DIR = DATA_DIR / 'results'

# OCR API 配置
OCR_API_URL = 'https://api.z.ai/api/paas/v4/layout_parsing'


class UploadFileView(APIView):
    """上传本地 PDF 或图片文件"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        api_key = request.data.get('api_key', '')
        ocr_prompt = request.data.get('ocr_prompt', '')

        if not file:
            return Response({'error': '请选择文件'}, status=status.HTTP_400_BAD_REQUEST)

        file_ext = file.name.lower().split('.')[-1] if '.' in file.name else ''
        project_id = uuid.uuid4().hex[:12]

        try:
            if file_ext == 'pdf':
                return self._process_pdf(request, file, file.name, project_id, api_key, ocr_prompt)
            else:
                return self._process_image(request, file, file.name, project_id, api_key, ocr_prompt)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_pdf(self, request, file, filename, project_id, api_key, ocr_prompt):
        """处理 PDF 文件"""
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        project_pages_dir = PAGES_DIR / project_id
        project_pages_dir.mkdir(exist_ok=True)

        # 保存上传的 PDF
        pdf_path = UPLOADS_DIR / f"{project_id}.pdf"
        with open(pdf_path, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)

        # 使用 PyMuPDF 转换 PDF 为图片
        try:
            doc = fitz.open(str(pdf_path))
            images = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                images.append(img_data)
            doc.close()
        except Exception as e:
            pdf_path.unlink(missing_ok=True)
            raise Exception(f"PDF 转换失败: {str(e)}")

        # 创建项目记录
        project = OCRProject.objects.create(
            id=project_id,
            user=request.user,
            name=filename,
            total_pages=len(images),
            api_key=api_key,
            ocr_prompt=ocr_prompt
        )

        # 保存页面图片
        for i, img_data in enumerate(images):
            page_num = i + 1
            img_path = project_pages_dir / f"page_{page_num}.png"
            with open(img_path, 'wb') as f:
                f.write(img_data)
            OCRPage.objects.create(
                project=project,
                page_num=page_num,
                image_path=str(img_path)
            )

        return Response({
            'project_id': project_id,
            'total_pages': len(images),
            'name': filename
        })

    def _process_image(self, request, file, filename, project_id, api_key, ocr_prompt):
        """处理图片文件"""
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        project_pages_dir = PAGES_DIR / project_id
        project_pages_dir.mkdir(exist_ok=True)

        valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        file_ext = '.' + filename.lower().split('.')[-1] if '.' in filename else ''

        if file_ext not in valid_extensions:
            return Response({
                'error': f'不支持的图片格式。支持的格式: {", ".join(valid_extensions)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        img_data = b''.join([chunk for chunk in file.chunks()])

        # 转换为 PNG 格式
        if file_ext != '.png':
            try:
                img = Image.open(BytesIO(img_data))
                output = BytesIO()
                img.save(output, format='PNG')
                img_data = output.getvalue()
            except Exception as e:
                raise Exception(f"图片转换失败: {str(e)}")

        page_num = 1
        final_img_path = project_pages_dir / f"page_{page_num}.png"
        with open(final_img_path, 'wb') as f:
            f.write(img_data)

        project = OCRProject.objects.create(
            id=project_id,
            user=request.user,
            name=filename,
            total_pages=1,
            api_key=api_key,
            ocr_prompt=ocr_prompt
        )

        OCRPage.objects.create(
            project=project,
            page_num=page_num,
            image_path=str(final_img_path)
        )

        return Response({
            'project_id': project_id,
            'total_pages': 1,
            'name': filename
        })


class UploadURLView(APIView):
    """从 URL 下载并处理文件"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        url = request.data.get('url', '')
        api_key = request.data.get('api_key', '')
        ocr_prompt = request.data.get('ocr_prompt', '')

        if not url:
            return Response({'error': '请提供 URL'}, status=status.HTTP_400_BAD_REQUEST)

        url_lower = url.lower()
        is_arxiv = 'arxiv.org' in url_lower

        if url_lower.endswith('.pdf') or is_arxiv:
            file_type = 'pdf'
            if is_arxiv:
                import re
                arxiv_match = re.search(r'/(\d+\.\d+)', url)
                if arxiv_match:
                    filename = f"arxiv_{arxiv_match.group(1)}.pdf"
                    if not url_lower.endswith('.pdf'):
                        arxiv_id = arxiv_match.group(1)
                        if 'arxiv.org/abs/' in url_lower:
                            url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                        elif '/pdf/' in url_lower:
                            url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
                else:
                    filename = "arxiv_paper.pdf"
            else:
                filename = url.split('/')[-1] or "document.pdf"
        elif any(url_lower.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']):
            file_type = 'image'
            filename = url.split('/')[-1] or "image.png"
        else:
            return Response({
                'error': 'URL 必须指向 PDF 或图片文件'
            }, status=status.HTTP_400_BAD_REQUEST)

        project_id = uuid.uuid4().hex[:12]

        # 下载文件
        try:
            response = requests.get(url, timeout=120)
            if response.status_code != 200:
                return Response({
                    'error': f'下载失败: HTTP {response.status_code}'
                }, status=status.HTTP_400_BAD_REQUEST)
            file_content = response.content
        except Exception as e:
            return Response({
                'error': f'下载失败: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)

        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        if file_type == 'pdf':
            file_path = UPLOADS_DIR / f"{project_id}.pdf"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return self._process_pdf_file(request, file_path, filename, project_id, api_key, ocr_prompt)
        else:
            file_path = UPLOADS_DIR / f"{project_id}_{filename}"
            with open(file_path, 'wb') as f:
                f.write(file_content)
            return self._process_image_file(request, file_path, filename, project_id, api_key, ocr_prompt)

    def _process_pdf_file(self, request, pdf_path, filename, project_id, api_key, ocr_prompt):
        """处理 PDF 文件（从 URL 下载）"""
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        project_pages_dir = PAGES_DIR / project_id
        project_pages_dir.mkdir(exist_ok=True)

        try:
            doc = fitz.open(str(pdf_path))
            images = []
            for page_num in range(doc.page_count):
                page = doc[page_num]
                mat = fitz.Matrix(1.5, 1.5)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("png")
                images.append(img_data)
            doc.close()
        except Exception as e:
            pdf_path.unlink(missing_ok=True)
            raise Exception(f"PDF 转换失败: {str(e)}")

        project = OCRProject.objects.create(
            id=project_id,
            user=request.user,
            name=filename,
            total_pages=len(images),
            api_key=api_key,
            ocr_prompt=ocr_prompt
        )

        for i, img_data in enumerate(images):
            page_num = i + 1
            img_path = project_pages_dir / f"page_{page_num}.png"
            with open(img_path, 'wb') as f:
                f.write(img_data)
            OCRPage.objects.create(
                project=project,
                page_num=page_num,
                image_path=str(img_path)
            )

        return Response({
            'project_id': project_id,
            'total_pages': len(images),
            'name': filename
        })

    def _process_image_file(self, request, img_path, filename, project_id, api_key, ocr_prompt):
        """处理图片文件（从 URL 下载）"""
        PAGES_DIR.mkdir(parents=True, exist_ok=True)
        project_pages_dir = PAGES_DIR / project_id
        project_pages_dir.mkdir(exist_ok=True)

        with open(img_path, 'rb') as f:
            img_data = f.read()

        file_ext = '.' + filename.lower().split('.')[-1] if '.' in filename else ''
        if file_ext != '.png':
            try:
                img = Image.open(BytesIO(img_data))
                output = BytesIO()
                img.save(output, format='PNG')
                img_data = output.getvalue()
            except Exception as e:
                raise Exception(f"图片转换失败: {str(e)}")

        page_num = 1
        final_img_path = project_pages_dir / f"page_{page_num}.png"
        with open(final_img_path, 'wb') as f:
            f.write(img_data)

        project = OCRProject.objects.create(
            id=project_id,
            user=request.user,
            name=filename,
            total_pages=1,
            api_key=api_key,
            ocr_prompt=ocr_prompt
        )

        OCRPage.objects.create(
            project=project,
            page_num=page_num,
            image_path=str(final_img_path)
        )

        return Response({
            'project_id': project_id,
            'total_pages': 1,
            'name': filename
        })


class ProjectsListView(APIView):
    """获取项目列表"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        projects = OCRProject.objects.all()
        data = []
        for p in projects:
            pages = p.pages.all()
            done = sum(1 for pg in pages if pg.ocr_status == 'done')
            errors = sum(1 for pg in pages if pg.ocr_status == 'error')
            processing = sum(1 for pg in pages if pg.ocr_status == 'processing')
            data.append({
                'id': p.id,
                'name': p.name,
                'total_pages': p.total_pages,
                'created_at': p.created_at.isoformat(),
                'progress': {
                    'done': done,
                    'error': errors,
                    'processing': processing,
                    'total': pages.count()
                }
            })
        return Response(data)


class ProjectDetailView(APIView):
    """获取项目详情"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        pages = project.pages.all()
        safe_pages = []
        for p in pages:
            safe_pages.append({
                'page_num': p.page_num,
                'ocr_status': p.ocr_status,
                'has_result': bool(p.ocr_result),
                'error_msg': p.error_msg
            })

        return Response({
            'id': project.id,
            'name': project.name,
            'total_pages': project.total_pages,
            'created_at': project.created_at.isoformat(),
            'pages': safe_pages
        })


class PageImageView(APIView):
    """获取页面图片"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id, page_num):
        try:
            page = OCRPage.objects.get(project__id=project_id, page_num=page_num)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        img_path = Path(page.image_path)
        if not img_path.exists():
            return Response({'error': '图片文件不存在'}, status=status.HTTP_404_NOT_FOUND)

        return FileResponse(img_path, content_type='image/png')


class SubmitOCRView(APIView):
    """提交 OCR 任务"""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        if project.user and project.user != request.user:
            return Response({'error': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        api_key = request.data.get('api_key', '') or project.api_key or ''
        if not api_key:
            return Response({'error': '请提供 API 密钥'}, status=status.HTTP_400_BAD_REQUEST)

        ocr_prompt = request.data.get('ocr_prompt', '') or project.ocr_prompt or ''

        # 更新项目的 API key 和 prompt
        if request.data.get('api_key'):
            project.api_key = api_key
        if request.data.get('ocr_prompt'):
            project.ocr_prompt = ocr_prompt
        project.save()

        selected_pages = request.data.get('pages', [])
        if not selected_pages:
            return Response({'error': '请选择要处理的页面'}, status=status.HTTP_400_BAD_REQUEST)

        pages = project.pages.filter(page_num__in=selected_pages).exclude(ocr_status__in=['processing', 'done'])

        import threading
        for page in pages:
            page.ocr_status = 'processing'
            page.submitted_at = timezone.now()
            page.save()

            thread = threading.Thread(
                target=self._process_page,
                args=(page, api_key, ocr_prompt)
            )
            thread.start()

        return Response({
            'submitted': pages.count(),
            'skipped': len(selected_pages) - pages.count()
        })

    def _process_page(self, page, api_key, prompt):
        """处理单个页面的 OCR"""
        try:
            result = self._call_ocr_api(api_key, page.image_path, prompt)
            page.ocr_result = result
            page.ocr_status = 'done'
            page.completed_at = timezone.now()
            page.error_msg = ''
        except Exception as e:
            page.ocr_status = 'error'
            page.error_msg = str(e)
            page.completed_at = timezone.now()
        page.save()

    def _call_ocr_api(self, api_key, image_path, prompt=''):
        """调用 OCR API"""
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "model": "glm-ocr",
            "file": f"data:image/png;base64,{img_data}"
        }

        if prompt and prompt.strip():
            payload["prompt"] = prompt.strip()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(OCR_API_URL, json=payload, headers=headers, timeout=120)
        if response.status_code != 200:
            raise Exception(f"API 错误 {response.status_code}: {response.text}")

        data = response.json()
        content = (data.get('md_results', '') or
                  data.get('data', {}).get('md_results', '') or
                  data.get('data', {}).get('content', '') or
                  data.get('content', ''))

        if not content and 'choices' in data:
            content = data['choices'][0].get('message', {}).get('content', '')

        return content or str(data)


class RetryPageView(APIView):
    """重试失败的页面"""
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id, page_num):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        if project.user and project.user != request.user:
            return Response({'error': '无权操作'}, status=status.HTTP_403_FORBIDDEN)

        api_key = project.api_key or ''
        if not api_key:
            return Response({'error': '未配置 API 密钥'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            page = project.pages.get(page_num=page_num)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        page.ocr_status = 'processing'
        page.error_msg = ''
        page.save()

        import threading
        thread = threading.Thread(
            target=self._process_page,
            args=(page, api_key, project.ocr_prompt or '')
        )
        thread.start()

        return Response({'status': 'retrying'})

    def _process_page(self, page, api_key, prompt):
        try:
            result = self._call_ocr_api(api_key, page.image_path, prompt)
            page.ocr_result = result
            page.ocr_status = 'done'
            page.completed_at = timezone.now()
            page.error_msg = ''
        except Exception as e:
            page.ocr_status = 'error'
            page.error_msg = str(e)
            page.completed_at = timezone.now()
        page.save()

    def _call_ocr_api(self, api_key, image_path, prompt=''):
        """调用 OCR API"""
        with open(image_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')

        payload = {
            "model": "glm-ocr",
            "file": f"data:image/png;base64,{img_data}"
        }

        if prompt and prompt.strip():
            payload["prompt"] = prompt.strip()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        response = requests.post(OCR_API_URL, json=payload, headers=headers, timeout=120)
        if response.status_code != 200:
            raise Exception(f"API 错误 {response.status_code}: {response.text}")

        data = response.json()
        content = (data.get('md_results', '') or
                  data.get('data', {}).get('md_results', '') or
                  data.get('data', {}).get('content', '') or
                  data.get('content', ''))

        if not content and 'choices' in data:
            content = data['choices'][0].get('message', {}).get('content', '')

        return content or str(data)


class StatusView(APIView):
    """获取项目状态"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        pages = project.pages.all()
        data = []
        for p in pages:
            data.append({
                'page_num': p.page_num,
                'status': p.ocr_status,
                'has_result': bool(p.ocr_result),
                'error': p.error_msg
            })
        return Response(data)


class ResultView(APIView):
    """获取完整 OCR 结果"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        pages = project.pages.filter(ocr_status='done').order_by('page_num')
        parts = []
        for p in pages:
            if p.ocr_result:
                parts.append(f"+-{p.page_num}-+\n\n{p.ocr_result}")

        md_content = "\n\n".join(parts)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_path = RESULTS_DIR / f"{project_id}.md"
        with open(result_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return Response({
            'content': md_content,
            'file': f"/api/ocr/projects/{project_id}/result/download"
        })


class DownloadResultView(APIView):
    """下载 Markdown 结果"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        result_path = RESULTS_DIR / f"{project_id}.md"

        if not result_path.exists():
            pages = project.pages.filter(ocr_status='done').order_by('page_num')
            parts = []
            for p in pages:
                if p.ocr_result:
                    parts.append(f"+-{p.page_num}-+\n\n{p.ocr_result}")
            md_content = "\n\n".join(parts)

            with open(result_path, 'w', encoding='utf-8') as f:
                f.write(md_content)
        else:
            with open(result_path, 'r', encoding='utf-8') as f:
                md_content = f.read()

        name = project.name.rsplit('.', 1)[0] if '.' in project.name else project_id
        response = FileResponse(result_path, content_type='text/markdown')
        response['Content-Disposition'] = f'attachment; filename="{name}.md"'
        return response


class PageResultView(APIView):
    """获取单页 OCR 结果"""
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id, page_num):
        try:
            page = OCRPage.objects.get(project__id=project_id, page_num=page_num)
        except OCRPage.DoesNotExist:
            return Response({'error': '页面不存在'}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            'content': page.ocr_result or '',
            'status': page.ocr_status
        })


class DeleteProjectView(APIView):
    """删除项目"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, project_id):
        try:
            project = OCRProject.objects.get(id=project_id)
        except OCRProject.DoesNotExist:
            return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        if project.user and project.user != request.user:
            return Response({'error': '无权部分'}, status=status.HTTP_403_FORBIDDEN)

        project_pages_dir = PAGES_DIR / project_id
        if project_pages_dir.exists():
            shutil.rmtree(project_pages_dir)

        pdf_path = UPLOADS_DIR / f"{project_id}.pdf"
        pdf_path.unlink(missing_ok=True)

        result_path = RESULTS_DIR / f"{project_id}.md"
        result_path.unlink(missing_ok=True)

        project.delete()

        return Response({'status': 'deleted'})
