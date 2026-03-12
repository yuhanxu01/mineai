import json
import time
from django.http import StreamingHttpResponse, JsonResponse
from django.views import View
from django.db.models import Sum, Count, Avg
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import KGProject, KGNode, KGEdge, KGCallLog
from .traversal import (
    keyword_search_nodes, bfs_subgraph, find_path,
    compute_node_ranks, format_subgraph_as_text, get_node_neighbors
)


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
