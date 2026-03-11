import json
from rest_framework.views import APIView
from rest_framework.response import Response
from novel.models import Project, Chapter
from novel import agent
from memory.pyramid import consolidate_universe
from memory.models import MemoryNode
from core.llm import chat
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from core.llm import chat


class ProjectListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        projects = Project.objects.all()
        return Response([{
            'id': p.id, 'title': p.title, 'genre': p.genre,
            'synopsis': p.synopsis[:200],
            'chapter_count': p.chapters.count(),
            'total_words': sum(c.word_count for c in p.chapters.all()),
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
        } for p in projects])

    def post(self, request):
        data = request.data
        project = Project.objects.create(
            user=request.user,
            title=data['title'], genre=data.get('genre', ''),
            synopsis=data.get('synopsis', ''),
            style_guide=data.get('style_guide', ''),
            world_setting=data.get('world_setting', ''),
        )
        MemoryNode.objects.create(
            project_id=project.id, level=0, node_type='narrative',
            title=f'故事宇宙: {project.title}',
            summary=f"标题: {project.title}\n类型: {project.genre}\n简介: {project.synopsis}",
            importance=1.0,
        )
        return Response({'id': project.id, 'title': project.title}, status=201)


class ProjectDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, project_id):
        try:
            p = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        chapters = Chapter.objects.filter(project=p)
        return Response({
            'id': p.id, 'title': p.title, 'genre': p.genre,
            'synopsis': p.synopsis, 'style_guide': p.style_guide,
            'world_setting': p.world_setting, 'metadata': p.metadata,
            'chapters': [{
                'id': c.id, 'number': c.number, 'title': c.title,
                'outline': c.outline, 'word_count': c.word_count,
                'status': c.status, 'memory_node_id': c.memory_node_id,
            } for c in chapters],
            'created_at': p.created_at.isoformat(),
        })

    def put(self, request, project_id):
        try:
            p = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        if p.user and p.user != request.user:
            return Response({"error": "无权操作"}, status=403)
        for field in ['title', 'genre', 'synopsis', 'style_guide', 'world_setting']:
            if field in request.data:
                setattr(p, field, request.data[field])
        p.save()
        return Response({"id": p.id, "updated": True})

    def delete(self, request, project_id):
        try:
            p = Project.objects.get(id=project_id)
            if p.user and p.user != request.user:
                return Response({"error": "无权操作"}, status=403)
            MemoryNode.objects.filter(project_id=project_id).delete()
            p.delete()
            return Response({"deleted": True})
        except Project.DoesNotExist:
            return Response({"error": "未找到"}, status=404)


class ChapterDetailView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, chapter_id):
        try:
            c = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        return Response({
            'id': c.id, 'project_id': c.project_id,
            'number': c.number, 'title': c.title,
            'outline': c.outline, 'content': c.content,
            'word_count': c.word_count, 'status': c.status,
            'memory_node_id': c.memory_node_id,
        })

    def put(self, request, chapter_id):
        try:
            c = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        if c.project.user and c.project.user != request.user:
            return Response({"error": "无权操作"}, status=403)
        for field in ['title', 'outline', 'content', 'status']:
            if field in request.data:
                setattr(c, field, request.data[field])
        c.save()
        return Response({"id": c.id, "updated": True, "word_count": c.word_count})


class ChapterCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return Response({"error": "项目未找到"}, status=404)
        if project.user and project.user != request.user:
            return Response({"error": "无权操作"}, status=403)
        data = request.data
        last = Chapter.objects.filter(project=project).order_by('-number').first()
        number = data.get('number', (last.number + 1) if last else 1)
        chapter = Chapter.objects.create(
            project=project, number=number,
            title=data.get('title', f'第{number}章'),
            outline=data.get('outline', ''),
        )
        mem_node = MemoryNode.objects.create(
            project_id=project_id, level=2, node_type='narrative',
            title=f"第{number}章: {chapter.title}",
            summary=chapter.outline or chapter.title,
            importance=0.7, chapter_index=number,
        )
        chapter.memory_node_id = mem_node.id
        chapter.save()
        return Response({'id': chapter.id, 'number': chapter.number}, status=201)


class WriteChapterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chapter_id):
        instruction = request.data.get('instruction', '')
        try:
            chapter = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        content = agent.write_chapter(chapter.project_id, chapter_id, instruction)
        return Response({'content': content, 'word_count': len(content.split()), 'chapter_id': chapter_id})


class ContinueWritingView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, chapter_id):
        instruction = request.data.get('instruction', '')
        try:
            chapter = Chapter.objects.get(id=chapter_id)
        except Chapter.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        content = agent.continue_writing(chapter.project_id, chapter_id, instruction)
        return Response({'content': content, 'word_count': len(content.split())})


class ChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        message = request.data.get('message', '')
        if not message:
            return Response({"error": "需要提供消息"}, status=400)
        response = agent.chat_with_agent(project_id, message)
        return Response({"response": response})


class GenerateOutlineView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        instruction = request.data.get('instruction', '')
        result = agent.generate_outline(project_id, instruction)
        if isinstance(result, str):
            return Response({"raw_response": result})
        return Response({"chapters": [{
            'id': c.id, 'number': c.number, 'title': c.title, 'outline': c.outline
        } for c in result]})


class ConsolidateProjectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, project_id):
        node = consolidate_universe(project_id)
        return Response({
            "id": node.id if node else None,
            "summary": node.summary[:500] if node else "没有可整合的内容",
        })


class GenerateIdeaView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        title = data.get('title', '').strip()
        genre = data.get('genre', '').strip()
        synopsis = data.get('synopsis', '').strip()
        style_guide = data.get('style_guide', '').strip()
        world_setting = data.get('world_setting', '').strip()

        prompt = "你是一个极具创意的网文金牌编辑。请你帮我头脑风暴并补全一部小说的创意设定。\n\n"
        if title or genre or synopsis or style_guide or world_setting:
            prompt += "用户已经提供了一些初步想法（请基于这些内容进行发散和补全）：\n"
            if title: prompt += f"- 书名：{title}\n"
            if genre: prompt += f"- 题材：{genre}\n"
            if synopsis: prompt += f"- 简介：{synopsis}\n"
            if style_guide: prompt += f"- 风格：{style_guide}\n"
            if world_setting: prompt += f"- 世界观：{world_setting}\n\n"
        else:
            prompt += "用户什么都没提供，请你**完全放飞自我**，随机生成一个具有爆款潜质、脑洞大开、设定极度新颖的小说创意。\n\n"

        prompt += """请以有效的JSON格式返回填充后的完整设定，包含以下字段：
{
  "title": "（书名，不超过15个字，吸引人）",
  "genre": "（如：赛博朋克+修仙，或：克苏鲁+末世等）",
  "synopsis": "（故事简介，起因、冲突、金手指或核心看点，约150字）",
  "style_guide": "（写作风格指导，如：节奏极快，杀伐果断，带点黑色幽默）",
  "world_setting": "（世界观设定，介绍背景、力量体系或核心规则，约200字）"
}
只返回JSON本身，不要有除了JSON之外的任何解释或说明代码块。"""

        try:
            response = chat(
                [{"role": "user", "content": prompt}],
                system="你是一个网文剧情策划专家，仅以有效JSON格式输出，不带markdown包裹。",
                temperature=0.9
            )
            
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()
                
            idea = json.loads(cleaned)
            return Response(idea)
        except json.JSONDecodeError:
            return Response({"error": "AI生成的格式不是有效的JSON", "raw": response}, status=500)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
