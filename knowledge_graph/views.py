import json
import time
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.db.models import Sum, Count, Avg
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import KGProject, KGNode, KGEdge, KGCallLog
from .traversal import (
    keyword_search_nodes, bfs_subgraph, find_path,
    compute_node_ranks, format_subgraph_as_text, get_node_neighbors
)


# ──────────────────────────── 平台默认知识图谱 ────────────────────────────
# 用户视角的功能地图，帮助新用户了解平台各应用的具体功能

_APP = '#5ac4b4'   # 应用节点 - 青色
_FEAT = '#c9a86c'  # 普通功能节点 - 金色
_AI = '#d49a5a'    # AI驱动功能 - 橙色

PLATFORM_KG_NODES = [
    # 网文写作
    {'id':'a1','label':'网文写作','type':'entity','color':_APP,'desc':'专为长篇小说设计的智能写作工作台'},
    {'id':'f1','label':'章节管理','type':'concept','color':_FEAT,'desc':'按章节组织故事内容，支持拖拽排序与快速跳转'},
    {'id':'f2','label':'角色图鉴','type':'concept','color':_FEAT,'desc':'维护角色档案：外貌、性格、关系网络，写作时随时查阅'},
    {'id':'f3','label':'无限记忆写作','type':'concept','color':_AI,'desc':'AI记住全书所有情节，续写时自动调用前文细节，不遗忘、不矛盾'},
    {'id':'f4','label':'故事时间线','type':'concept','color':_FEAT,'desc':'可视化展示事件发生顺序，梳理剧情结构'},
    {'id':'f5','label':'伏笔追踪','type':'concept','color':_FEAT,'desc':'标记和追踪全书伏笔，提醒何时需要回收'},
    {'id':'f6','label':'剧情顾问 AI','type':'concept','color':_AI,'desc':'与 AI 共同讨论剧情走向、角色成长、冲突设计'},
    # 学术研究站
    {'id':'a2','label':'学术研究站','type':'entity','color':_APP,'desc':'文献管理与研究写作一体化工作台'},
    {'id':'f7','label':'文献导入','type':'concept','color':_FEAT,'desc':'导入 PDF 论文，自动解析元数据与全文'},
    {'id':'f8','label':'零幻觉引用','type':'concept','color':_AI,'desc':'AI回答时只引用已上传文献中的真实内容，不编造'},
    {'id':'f9','label':'六类研究笔记','type':'concept','color':_FEAT,'desc':'注释、摘要、评论、问题、洞见、关联六种笔记类型'},
    {'id':'f10','label':'知识探索','type':'concept','color':_AI,'desc':'在文献知识库中用自然语言提问，快速定位相关段落'},
    {'id':'f11','label':'论文写作辅助','type':'concept','color':_AI,'desc':'基于读过的文献生成综述、摘要与论证段落'},
    # 知识图谱
    {'id':'a3','label':'知识图谱','type':'entity','color':_APP,'desc':'将知识可视化为节点和关系网络'},
    {'id':'f12','label':'AI 自动提取','type':'concept','color':_AI,'desc':'粘贴任意文本，AI 自动识别概念、实体和关系建图'},
    {'id':'f13','label':'交互图谱可视化','type':'concept','color':_FEAT,'desc':'力导向布局，鼠标悬停高亮关联，点击查看详情'},
    {'id':'f14','label':'概念路径查找','type':'concept','color':_FEAT,'desc':'在两个概念之间寻找知识推导路径'},
    {'id':'f15','label':'知识问答','type':'concept','color':_AI,'desc':'基于图谱内容回答问题，只说图谱里有的知识'},
    {'id':'f16','label':'重要度排名','type':'concept','color':_FEAT,'desc':'PageRank 算法计算节点中心性，发现核心概念'},
    # 代码助手
    {'id':'a4','label':'代码助手','type':'entity','color':_APP,'desc':'本地代码库的 AI 重构与理解工具'},
    {'id':'f17','label':'本地目录模式','type':'concept','color':_FEAT,'desc':'直接上传整个项目文件夹，无需逐文件操作'},
    {'id':'f18','label':'AI 重构建议','type':'concept','color':_AI,'desc':'AI 分析代码后给出重构方案，说明原因与改动点'},
    {'id':'f19','label':'逐行 Diff 审查','type':'concept','color':_FEAT,'desc':'AI 提出修改时以 Diff 展示，可逐块接受或拒绝'},
    {'id':'f20','label':'版本历史回溯','type':'concept','color':_FEAT,'desc':'每次修改自动保存快照，随时回到任意历史版本'},
    {'id':'f21','label':'跨文件理解','type':'concept','color':_AI,'desc':'AI 理解多文件间的调用关系，给出全局优化建议'},
    # Claude Bridge
    {'id':'a5','label':'Claude Bridge','type':'entity','color':_APP,'desc':'让 Claude AI 直接操作你的本地电脑'},
    {'id':'f22','label':'远程接入本地','type':'concept','color':_FEAT,'desc':'通过浏览器让 Claude 访问本机文件和终端'},
    {'id':'f23','label':'工具调用可视化','type':'concept','color':_FEAT,'desc':'实时展示 AI 正在调用哪些工具、传入什么参数'},
    {'id':'f24','label':'操作权限管控','type':'concept','color':_FEAT,'desc':'自定义允许/禁止 AI 执行的操作类型'},
    {'id':'f25','label':'Diff 预览','type':'concept','color':_FEAT,'desc':'AI 修改文件前先展示变更内容，确认后再写入'},
    # 扫描增强
    {'id':'a6','label':'扫描增强','type':'entity','color':_APP,'desc':'手机拍摄的文档图片专业级增强处理'},
    {'id':'f26','label':'曲面平整化','type':'concept','color':_FEAT,'desc':'修正书页弯曲变形，将曲面文字还原为平面'},
    {'id':'f27','label':'透视校正','type':'concept','color':_FEAT,'desc':'自动检测并矫正拍摄角度偏斜导致的梯形变形'},
    {'id':'f28','label':'自动纠偏','type':'concept','color':_FEAT,'desc':'检测文字倾斜角度并旋转至水平，提升可读性'},
    {'id':'f29','label':'智能降噪','type':'concept','color':_FEAT,'desc':'去除纸张纹理、光斑和拍摄噪点'},
    {'id':'f30','label':'文档二值化','type':'concept','color':_FEAT,'desc':'自适应阈值将图片转为黑白，使文字清晰印刷级'},
    {'id':'f31','label':'对比度增强','type':'concept','color':_FEAT,'desc':'提升文字与背景的对比度，改善打印和识别效果'},
    {'id':'f32','label':'隐私保护处理','type':'concept','color':_FEAT,'desc':'在本地完成所有处理，图片不上传至任何服务器'},
    # OCR 工作室
    {'id':'a7','label':'OCR 工作室','type':'entity','color':_APP,'desc':'图片和 PDF 文字识别提取工具'},
    {'id':'f33','label':'图片文字识别','type':'concept','color':_AI,'desc':'AI 识别照片或截图中的文字，支持中英文混排'},
    {'id':'f34','label':'PDF 文本提取','type':'concept','color':_FEAT,'desc':'从 PDF 文件中精确提取可编辑文本内容'},
    {'id':'f35','label':'多格式输出','type':'concept','color':_FEAT,'desc':'识别结果可导出为纯文本、Markdown 或 Word 格式'},
    # AI 题库
    {'id':'a8','label':'AI 题库','type':'entity','color':_APP,'desc':'拍照解题并沉淀知识的学习工具'},
    {'id':'f36','label':'拍题识别','type':'concept','color':_AI,'desc':'拍摄题目图片，AI 自动识别题目内容'},
    {'id':'f37','label':'多模型解答','type':'concept','color':_AI,'desc':'同时向多个 AI 模型提问，对比不同解题思路'},
    {'id':'f38','label':'最终答案沉淀','type':'concept','color':_FEAT,'desc':'确认最佳答案后保存至题库，便于复习'},
    {'id':'f39','label':'共享题库','type':'concept','color':_FEAT,'desc':'浏览其他用户分享的题目与解答，共同积累知识'},
]

PLATFORM_KG_EDGES = [
    # 网文写作
    {'s':'a1','t':'f1','r':'has_method'}, {'s':'a1','t':'f2','r':'has_method'},
    {'s':'a1','t':'f3','r':'has_method'}, {'s':'a1','t':'f4','r':'has_method'},
    {'s':'a1','t':'f5','r':'has_method'}, {'s':'a1','t':'f6','r':'has_method'},
    {'s':'f3','t':'f6','r':'extends'},   # 无限记忆写作 → 剧情顾问
    {'s':'f4','t':'f5','r':'related_to'},# 时间线 → 伏笔
    # 学术研究站
    {'s':'a2','t':'f7','r':'has_method'}, {'s':'a2','t':'f8','r':'has_method'},
    {'s':'a2','t':'f9','r':'has_method'}, {'s':'a2','t':'f10','r':'has_method'},
    {'s':'a2','t':'f11','r':'has_method'},
    {'s':'f7','t':'f8','r':'leads_to'},  # 文献导入 → 零幻觉引用
    {'s':'f10','t':'f9','r':'leads_to'}, # 知识探索 → 研究笔记
    # 知识图谱
    {'s':'a3','t':'f12','r':'has_method'}, {'s':'a3','t':'f13','r':'has_method'},
    {'s':'a3','t':'f14','r':'has_method'}, {'s':'a3','t':'f15','r':'has_method'},
    {'s':'a3','t':'f16','r':'has_method'},
    {'s':'f12','t':'f13','r':'leads_to'}, # 自动提取 → 可视化
    {'s':'f16','t':'f14','r':'extends'},  # 重要度排名 → 路径查找
    # 代码助手
    {'s':'a4','t':'f17','r':'has_method'}, {'s':'a4','t':'f18','r':'has_method'},
    {'s':'a4','t':'f19','r':'has_method'}, {'s':'a4','t':'f20','r':'has_method'},
    {'s':'a4','t':'f21','r':'has_method'},
    {'s':'f17','t':'f21','r':'leads_to'}, # 目录模式 → 跨文件理解
    {'s':'f18','t':'f19','r':'leads_to'}, # 重构建议 → Diff 审查
    # Claude Bridge
    {'s':'a5','t':'f22','r':'has_method'}, {'s':'a5','t':'f23','r':'has_method'},
    {'s':'a5','t':'f24','r':'has_method'}, {'s':'a5','t':'f25','r':'has_method'},
    {'s':'f22','t':'f23','r':'leads_to'}, {'s':'f24','t':'f25','r':'extends'},
    # 扫描增强
    {'s':'a6','t':'f26','r':'has_method'}, {'s':'a6','t':'f27','r':'has_method'},
    {'s':'a6','t':'f28','r':'has_method'}, {'s':'a6','t':'f29','r':'has_method'},
    {'s':'a6','t':'f30','r':'has_method'}, {'s':'a6','t':'f31','r':'has_method'},
    {'s':'a6','t':'f32','r':'has_method'},
    {'s':'f27','t':'f28','r':'leads_to'}, {'s':'f29','t':'f30','r':'leads_to'},
    # OCR 工作室
    {'s':'a7','t':'f33','r':'has_method'}, {'s':'a7','t':'f34','r':'has_method'},
    {'s':'a7','t':'f35','r':'has_method'},
    {'s':'f33','t':'f35','r':'leads_to'},
    # AI 题库
    {'s':'a8','t':'f36','r':'has_method'}, {'s':'a8','t':'f37','r':'has_method'},
    {'s':'a8','t':'f38','r':'has_method'}, {'s':'a8','t':'f39','r':'has_method'},
    {'s':'f36','t':'f37','r':'leads_to'}, {'s':'f37','t':'f38','r':'leads_to'},
    # 跨应用工作流
    {'s':'a6','t':'a7','r':'leads_to'},  # 扫描增强 → OCR 工作室
    {'s':'a7','t':'a2','r':'leads_to'},  # OCR 工作室 → 学术研究站
    {'s':'a2','t':'a3','r':'leads_to'},  # 学术研究站 → 知识图谱
    {'s':'a8','t':'a6','r':'related_to'},# AI题库 → 扫描增强（拍题）
]


def _build_platform_elements():
    nodes = []
    for n in PLATFORM_KG_NODES:
        nodes.append({
            'data': {
                'id': n['id'], 'label': n['label'],
                'type': n['type'], 'color': n['color'],
                'description': n['desc'], 'importance': 0.8 if n['id'].startswith('a') else 0.5,
            }
        })
    edges = []
    for i, e in enumerate(PLATFORM_KG_EDGES):
        edges.append({
            'data': {'id': f'pe{i}', 'source': e['s'], 'target': e['t'], 'relation': e['r']}
        })
    return nodes, edges


class PlatformKGOverviewView(APIView):
    """平台默认功能图谱 — 无需认证，任何人可访问"""
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        nodes, edges = _build_platform_elements()
        return Response({'nodes': nodes, 'edges': edges})


class PlatformKGCloneView(APIView):
    """将平台图谱克隆为当前用户的个人可编辑副本"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        nodes, edges = _build_platform_elements()
        proj = KGProject.objects.create(
            user=request.user,
            title='平台功能图谱（副本）',
            description='从平台内置图谱克隆，可自由编辑',
            source_app='manual',
            is_platform_default=False,
        )
        # 建立节点
        node_map = {}
        for nd in nodes:
            d = nd['data']
            obj = KGNode.objects.create(
                kg_project=proj,
                label=d['label'],
                node_type=d['type'],
                description=d.get('description', ''),
                importance=d.get('importance', 0.5),
                metadata={'color': d.get('color', '')},
            )
            node_map[d['id']] = obj.id
        # 建立边
        for ed in edges:
            d = ed['data']
            src_id = node_map.get(d['source'])
            tgt_id = node_map.get(d['target'])
            if src_id and tgt_id:
                KGEdge.objects.create(
                    kg_project=proj,
                    source_id=src_id,
                    target_id=tgt_id,
                    relation_type=d.get('relation', 'related_to'),
                )
        proj.node_count = len(nodes)
        proj.edge_count = len(edges)
        proj.save(update_fields=['node_count', 'edge_count'])
        return Response({'id': proj.id, 'title': proj.title}, status=201)


# ──────────────────────────── 图谱项目 ────────────────────────────

class KGProjectListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = KGProject.objects.filter(user=request.user)
        data = [{
            'id': p.id,
            'title': p.title,
            'description': p.description,
            'source_app': p.source_app,
            'source_project_id': p.source_project_id,
            'node_count': p.node_count,
            'edge_count': p.edge_count,
            'is_shared': p.is_shared,
            'created_at': p.created_at.isoformat(),
            'updated_at': p.updated_at.isoformat(),
        } for p in projects]
        return Response(data)

    def post(self, request):
        d = request.data
        proj = KGProject.objects.create(
            user=request.user,
            title=d.get('title', '新知识图谱'),
            description=d.get('description', ''),
            source_app=d.get('source_app', 'manual'),
            source_project_id=d.get('source_project_id'),
            is_shared=d.get('is_shared', False),
        )
        return Response({'id': proj.id, 'title': proj.title}, status=201)


class KGProjectDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def _get(self, kg_id, user):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != user.id and not kg.is_shared:
                return None, Response({'error': '无权限'}, status=403)
            return kg, None
        except KGProject.DoesNotExist:
            return None, Response({'error': '不存在'}, status=404)

    def get(self, request, kg_id):
        kg, err = self._get(kg_id, request.user)
        if err:
            return err
        # 刷新计数
        kg.node_count = kg.nodes.count()
        kg.edge_count = kg.edges.count()
        return Response({
            'id': kg.id,
            'title': kg.title,
            'description': kg.description,
            'source_app': kg.source_app,
            'source_project_id': kg.source_project_id,
            'node_count': kg.node_count,
            'edge_count': kg.edge_count,
            'is_shared': kg.is_shared,
            'metadata': kg.metadata,
            'created_at': kg.created_at.isoformat(),
            'updated_at': kg.updated_at.isoformat(),
        })

    def patch(self, request, kg_id):
        kg, err = self._get(kg_id, request.user)
        if err:
            return err
        if kg.user_id != request.user.id:
            return Response({'error': '无权限'}, status=403)
        d = request.data
        for field in ['title', 'description', 'is_shared']:
            if field in d:
                setattr(kg, field, d[field])
        kg.save()
        return Response({'ok': True})

    def delete(self, request, kg_id):
        kg, err = self._get(kg_id, request.user)
        if err:
            return err
        if kg.user_id != request.user.id:
            return Response({'error': '无权限'}, status=403)
        kg.delete()
        return Response({'ok': True})


# ──────────────────────────── 节点管理 ────────────────────────────

class KGNodeListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        node_type = request.GET.get('type')
        search = request.GET.get('q', '')
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))

        qs = KGNode.objects.filter(kg_project_id=kg_id)
        if node_type:
            qs = qs.filter(node_type=node_type)
        if search:
            from django.db.models import Q
            qs = qs.filter(Q(label__icontains=search) | Q(description__icontains=search))

        total = qs.count()
        nodes = qs.order_by('-importance')[offset:offset + limit]

        return Response({
            'total': total,
            'nodes': [{
                'id': n.id,
                'label': n.label,
                'node_type': n.node_type,
                'description': n.description,
                'importance': n.importance,
                'visit_count': n.visit_count,
                'source_ref': n.source_ref,
                'keywords': n.keywords,
                'aliases': n.aliases,
                'created_at': n.created_at.isoformat(),
            } for n in nodes]
        })

    def post(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id, user=request.user)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        d = request.data
        label = d.get('label', '').strip()
        if not label:
            return Response({'error': '标签不能为空'}, status=400)

        node, created = KGNode.objects.get_or_create(
            kg_project=kg,
            label=label,
            defaults={
                'node_type': d.get('node_type', 'concept'),
                'description': d.get('description', ''),
                'keywords': d.get('keywords', []),
                'aliases': d.get('aliases', []),
                'source_ref': d.get('source_ref', ''),
            }
        )

        if created:
            kg.node_count = kg.nodes.count()
            kg.save(update_fields=['node_count', 'updated_at'])

        KGCallLog.record(
            user=request.user, kg_project=kg,
            operation='add_node', caller_app='manual',
            nodes_created=1 if created else 0,
        )

        return Response({'id': node.id, 'created': created}, status=201 if created else 200)


class KGNodeDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, kg_id, node_id):
        try:
            node = KGNode.objects.get(id=node_id, kg_project_id=kg_id)
        except KGNode.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        # 获取邻居
        neighbors = get_node_neighbors(kg_id, node_id, max_neighbors=10)

        return Response({
            'id': node.id,
            'label': node.label,
            'node_type': node.node_type,
            'description': node.description,
            'importance': node.importance,
            'visit_count': node.visit_count,
            'source_ref': node.source_ref,
            'source_lit_id': node.source_lit_id,
            'keywords': node.keywords,
            'aliases': node.aliases,
            'metadata': node.metadata,
            'created_at': node.created_at.isoformat(),
            'out_edges': [{
                'edge_id': e.id,
                'relation': e.relation_type,
                'relation_label': e.get_relation_type_display(),
                'target_id': e.target_id,
                'target_label': e.target.label,
                'weight': e.weight,
            } for e in neighbors['out_edges']],
            'in_edges': [{
                'edge_id': e.id,
                'relation': e.relation_type,
                'relation_label': e.get_relation_type_display(),
                'source_id': e.source_id,
                'source_label': e.source.label,
                'weight': e.weight,
            } for e in neighbors['in_edges']],
        })

    def patch(self, request, kg_id, node_id):
        try:
            kg = KGProject.objects.get(id=kg_id, user=request.user)
            node = KGNode.objects.get(id=node_id, kg_project=kg)
        except (KGProject.DoesNotExist, KGNode.DoesNotExist):
            return Response({'error': '不存在'}, status=404)

        d = request.data
        for field in ['label', 'node_type', 'description', 'keywords', 'aliases', 'source_ref']:
            if field in d:
                setattr(node, field, d[field])
        node.save()
        return Response({'ok': True})

    def delete(self, request, kg_id, node_id):
        try:
            kg = KGProject.objects.get(id=kg_id, user=request.user)
            node = KGNode.objects.get(id=node_id, kg_project=kg)
        except (KGProject.DoesNotExist, KGNode.DoesNotExist):
            return Response({'error': '不存在'}, status=404)

        node.delete()
        kg.node_count = kg.nodes.count()
        kg.edge_count = kg.edges.count()
        kg.save(update_fields=['node_count', 'edge_count', 'updated_at'])
        return Response({'ok': True})


# ──────────────────────────── 边管理 ────────────────────────────

class KGEdgeListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        limit = int(request.GET.get('limit', 200))
        offset = int(request.GET.get('offset', 0))
        relation_type = request.GET.get('relation')

        qs = KGEdge.objects.filter(kg_project_id=kg_id).select_related('source', 'target')
        if relation_type:
            qs = qs.filter(relation_type=relation_type)

        total = qs.count()
        edges = qs[offset:offset + limit]

        return Response({
            'total': total,
            'edges': [{
                'id': e.id,
                'source_id': e.source_id,
                'source_label': e.source.label,
                'target_id': e.target_id,
                'target_label': e.target.label,
                'relation_type': e.relation_type,
                'relation_label': e.get_relation_type_display(),
                'weight': e.weight,
                'confidence': e.confidence,
                'description': e.description,
                'source_citation': e.source_citation,
            } for e in edges]
        })

    def post(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id, user=request.user)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        d = request.data
        try:
            src = KGNode.objects.get(id=d['source_id'], kg_project=kg)
            tgt = KGNode.objects.get(id=d['target_id'], kg_project=kg)
        except (KGNode.DoesNotExist, KeyError):
            return Response({'error': '节点不存在'}, status=400)

        edge, created = KGEdge.objects.get_or_create(
            kg_project=kg,
            source=src,
            target=tgt,
            relation_type=d.get('relation_type', 'related_to'),
            defaults={
                'weight': d.get('weight', 1.0),
                'confidence': d.get('confidence', 0.8),
                'description': d.get('description', ''),
                'source_citation': d.get('source_citation', ''),
            }
        )

        if created:
            kg.edge_count = kg.edges.count()
            kg.save(update_fields=['edge_count', 'updated_at'])

        KGCallLog.record(
            user=request.user, kg_project=kg,
            operation='add_edge', caller_app='manual',
            edges_created=1 if created else 0,
        )

        return Response({'id': edge.id, 'created': created}, status=201 if created else 200)


class KGEdgeDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, kg_id, edge_id):
        try:
            kg = KGProject.objects.get(id=kg_id, user=request.user)
            edge = KGEdge.objects.get(id=edge_id, kg_project=kg)
        except (KGProject.DoesNotExist, KGEdge.DoesNotExist):
            return Response({'error': '不存在'}, status=404)

        edge.delete()
        kg.edge_count = kg.edges.count()
        kg.save(update_fields=['edge_count', 'updated_at'])
        return Response({'ok': True})


# ──────────────────────────── 图谱可视化数据 ────────────────────────────

class KGGraphDataView(APIView):
    """返回Cytoscape.js格式的图谱数据"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        max_nodes = int(request.GET.get('max_nodes', 200))

        # 按重要度取top节点
        nodes = list(KGNode.objects.filter(kg_project_id=kg_id)
                     .order_by('-importance')[:max_nodes])
        node_ids = {n.id for n in nodes}

        # 只取这些节点间的边
        edges = list(KGEdge.objects.filter(
            kg_project_id=kg_id,
            source_id__in=node_ids,
            target_id__in=node_ids,
        ).select_related('source', 'target'))

        cyto_elements = [n.to_cytoscape() for n in nodes]
        cyto_elements += [e.to_cytoscape() for e in edges]

        return Response({
            'elements': cyto_elements,
            'node_count': len(nodes),
            'edge_count': len(edges),
        })


# ──────────────────────────── 检索与探索 ────────────────────────────

class KGSearchView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        t0 = time.time()
        query = request.data.get('query', '')
        top_k = int(request.data.get('top_k', 15))
        node_types = request.data.get('node_types')

        nodes = keyword_search_nodes(kg_id, query, top_k=top_k, node_types=node_types)
        duration_ms = int((time.time() - t0) * 1000)

        KGCallLog.record(
            user=request.user, kg_project=kg,
            operation='search_nodes', caller_app='api',
            input_length=len(query),
            result_nodes=len(nodes),
            nodes_traversed=len(nodes),
            duration_ms=duration_ms,
        )

        return Response({
            'nodes': [{
                'id': n.id,
                'label': n.label,
                'node_type': n.node_type,
                'description': n.description,
                'importance': n.importance,
                'source_ref': n.source_ref,
            } for n in nodes],
            'duration_ms': duration_ms,
        })


class KGSubgraphView(APIView):
    """查询以某些节点为中心的子图"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        t0 = time.time()
        seed_ids = request.data.get('seed_ids', [])
        seed_labels = request.data.get('seed_labels', [])
        max_depth = int(request.data.get('max_depth', 2))
        max_nodes = int(request.data.get('max_nodes', 50))
        edge_types = request.data.get('edge_types')

        # label转id
        all_seed_ids = list(seed_ids)
        for label in (seed_labels or []):
            found = keyword_search_nodes(kg_id, label, top_k=3)
            all_seed_ids.extend([n.id for n in found])

        if not all_seed_ids:
            # 返回最重要的节点
            top_nodes = list(KGNode.objects.filter(kg_project_id=kg_id)
                             .order_by('-importance')[:5])
            all_seed_ids = [n.id for n in top_nodes]

        result = bfs_subgraph(kg_id, all_seed_ids, max_depth=max_depth,
                              max_nodes=max_nodes, edge_types=edge_types)
        duration_ms = int((time.time() - t0) * 1000)

        KGCallLog.record(
            user=request.user, kg_project=kg,
            operation='bfs_traverse', caller_app='api',
            nodes_traversed=result['nodes_traversed'],
            edges_traversed=result['edges_traversed'],
            result_nodes=len(result['nodes']),
            duration_ms=duration_ms,
        )

        elements = [n.to_cytoscape() for n in result['nodes']]
        elements += [e.to_cytoscape() for e in result['edges']]

        return Response({
            'elements': elements,
            'stats': {
                'nodes': len(result['nodes']),
                'edges': len(result['edges']),
                'nodes_traversed': result['nodes_traversed'],
                'edges_traversed': result['edges_traversed'],
                'duration_ms': duration_ms,
            }
        })


class KGPathView(APIView):
    """路径搜索"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kg_id):
        try:
            kg = KGProject.objects.get(id=kg_id)
            if kg.user_id != request.user.id and not kg.is_shared:
                return Response({'error': '无权限'}, status=403)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        source_label = request.data.get('source', '')
        target_label = request.data.get('target', '')

        if not source_label or not target_label:
            return Response({'error': '请提供source和target'}, status=400)

        t0 = time.time()
        result = find_path(kg_id, source_label, target_label)
        duration_ms = int((time.time() - t0) * 1000)

        if not result:
            return Response({'found': False, 'duration_ms': duration_ms})

        nodes = list(KGNode.objects.filter(id__in=result['path']))
        edges = list(KGEdge.objects.filter(id__in=result['edges']).select_related('source', 'target'))

        return Response({
            'found': True,
            'length': result['length'],
            'path_nodes': [{'id': n.id, 'label': n.label, 'type': n.node_type} for n in nodes],
            'path_edges': [{
                'id': e.id,
                'source': e.source.label,
                'target': e.target.label,
                'relation': e.get_relation_type_display(),
            } for e in edges],
            'duration_ms': duration_ms,
        })


# ──────────────────────────── AI功能 ────────────────────────────

class KGExtractView(APIView):
    """从文本提取知识到图谱"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kg_id):
        try:
            KGProject.objects.get(id=kg_id, user=request.user)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        text = request.data.get('text', '')
        source_ref = request.data.get('source_ref', '')
        source_lit_id = request.data.get('source_lit_id')

        if not text.strip():
            return Response({'error': '文本不能为空'}, status=400)

        from .agent import extract_kg_from_text
        result = extract_kg_from_text(
            user=request.user,
            kg_project_id=kg_id,
            text=text,
            source_ref=source_ref,
            caller_app='manual',
            source_lit_id=source_lit_id,
        )
        return Response(result)


class KGChatStreamView(View):
    """知识图谱对话（流式）"""

    def post(self, request, kg_id):
        from rest_framework.authentication import TokenAuthentication
        from rest_framework.exceptions import AuthenticationFailed

        auth = TokenAuthentication()
        try:
            user_auth = auth.authenticate(request)
            if not user_auth:
                return JsonResponse({'error': '未认证'}, status=401)
            user = user_auth[0]
        except AuthenticationFailed:
            return JsonResponse({'error': '认证失败'}, status=401)

        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({'error': '无效请求'}, status=400)

        question = body.get('question', '')
        if not question:
            return JsonResponse({'error': '问题不能为空'}, status=400)

        from .agent import answer_with_kg_stream

        def stream_gen():
            for chunk in answer_with_kg_stream(user, int(kg_id), question):
                yield chunk

        return StreamingHttpResponse(
            stream_gen(),
            content_type='text/event-stream',
        )


class KGComputeRankView(APIView):
    """计算节点PageRank重要度"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, kg_id):
        try:
            KGProject.objects.get(id=kg_id, user=request.user)
        except KGProject.DoesNotExist:
            return Response({'error': '不存在'}, status=404)

        kg = KGProject.objects.get(id=kg_id, user=request.user)
        t0 = time.time()
        updated = compute_node_ranks(kg_id, iterations=10)
        duration_ms = int((time.time() - t0) * 1000)

        KGCallLog.record(
            user=request.user, kg_project=kg,
            operation='compute_rank', caller_app='manual',
            nodes_traversed=updated,
            duration_ms=duration_ms,
        )

        return Response({'updated': updated, 'duration_ms': duration_ms})


# ──────────────────────────── 统计 ────────────────────────────

class KGStatsView(APIView):
    """知识图谱使用统计"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        kg_id = request.GET.get('kg_id')
        days = int(request.GET.get('days', 30))

        from django.utils import timezone
        from datetime import timedelta
        since = timezone.now() - timedelta(days=days)

        qs = KGCallLog.objects.filter(user=request.user, created_at__gte=since)
        if kg_id:
            qs = qs.filter(kg_project_id=kg_id)

        total_calls = qs.count()
        agg = qs.aggregate(
            total_duration_ms=Sum('duration_ms'),
            total_tokens_in=Sum('llm_tokens_input'),
            total_tokens_out=Sum('llm_tokens_output'),
            total_nodes_traversed=Sum('nodes_traversed'),
            total_edges_traversed=Sum('edges_traversed'),
            avg_duration_ms=Avg('duration_ms'),
        )

        by_operation = list(
            qs.values('operation').annotate(
                count=Count('id'),
                total_ms=Sum('duration_ms'),
                total_tokens=Sum('llm_tokens_input') + Sum('llm_tokens_output'),
            ).order_by('-count')
        )

        by_caller = list(
            qs.values('caller_app').annotate(count=Count('id')).order_by('-count')
        )

        recent_logs = list(qs.order_by('-created_at')[:20].values(
            'id', 'operation', 'caller_app', 'duration_ms',
            'nodes_created', 'edges_created', 'nodes_traversed',
            'llm_tokens_input', 'llm_tokens_output', 'success', 'created_at'
        ))

        return Response({
            'total_calls': total_calls,
            'aggregates': {k: v or 0 for k, v in agg.items()},
            'by_operation': by_operation,
            'by_caller': by_caller,
            'recent_logs': recent_logs,
            'period_days': days,
        })
