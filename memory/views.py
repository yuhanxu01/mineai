from rest_framework.views import APIView
from rest_framework.response import Response
from memory.models import (
    MemoryNode, MemorySnapshot, MemoryLink, Character,
    CharacterSnapshot, CharacterRelation, TimelineEvent
)
from memory import pyramid


class PyramidStatsView(APIView):
    def get(self, request, project_id):
        return Response(pyramid.get_pyramid_stats(project_id))


class PyramidTreeView(APIView):
    def get(self, request, project_id):
        return Response(pyramid.get_pyramid_tree(project_id))


class MemoryNodeListView(APIView):
    def get(self, request, project_id):
        level = request.query_params.get('level')
        node_type = request.query_params.get('type')
        limit = int(request.query_params.get('limit', 50))
        qs = MemoryNode.objects.filter(project_id=project_id)
        if level is not None:
            qs = qs.filter(level=int(level))
        if node_type:
            qs = qs.filter(node_type=node_type)
        return Response([{
            'id': n.id, 'parent_id': n.parent_id, 'level': n.level,
            'level_name': n.level_name, 'node_type': n.node_type,
            'title': n.title, 'summary': n.summary[:500],
            'importance': n.importance, 'access_count': n.access_count,
            'version': n.version, 'chapter_index': n.chapter_index,
            'children_count': n.children.count(),
            'created_at': n.created_at.isoformat(),
        } for n in qs[:limit]])


class MemoryNodeDetailView(APIView):
    def get(self, request, node_id):
        try:
            n = MemoryNode.objects.get(id=node_id)
        except MemoryNode.DoesNotExist:
            return Response({"error": "未找到"}, status=404)

        children = n.children.all()[:20]
        links_out = MemoryLink.objects.filter(source=n)[:10]
        links_in = MemoryLink.objects.filter(target=n)[:10]
        snapshots = MemorySnapshot.objects.filter(node=n).order_by('version')

        return Response({
            'id': n.id, 'parent_id': n.parent_id, 'level': n.level,
            'level_name': n.level_name, 'node_type': n.node_type,
            'title': n.title, 'summary': n.summary, 'content': n.content,
            'importance': n.importance, 'access_count': n.access_count,
            'version': n.version, 'chapter_index': n.chapter_index,
            'metadata': n.metadata,
            'children': [{'id': c.id, 'title': c.title, 'level': c.level, 'level_name': c.level_name} for c in children],
            'links': [
                {'id': l.id, 'target_id': l.target_id, 'target_title': l.target.title,
                 'link_type': l.link_type, 'weight': l.weight} for l in links_out
            ] + [
                {'id': l.id, 'source_id': l.source_id, 'source_title': l.source.title,
                 'link_type': l.link_type, 'weight': l.weight, 'direction': 'incoming'} for l in links_in
            ],
            'snapshots': [
                {'version': s.version, 'summary': s.summary[:300], 'chapter_index': s.chapter_index,
                 'change_reason': s.change_reason, 'created_at': s.created_at.isoformat()} for s in snapshots
            ],
            'created_at': n.created_at.isoformat(),
            'updated_at': n.updated_at.isoformat(),
        })

    def delete(self, request, node_id):
        try:
            MemoryNode.objects.get(id=node_id).delete()
            return Response({"deleted": True})
        except MemoryNode.DoesNotExist:
            return Response({"error": "未找到"}, status=404)


class MemoryNodeEditAgentView(APIView):
    def post(self, request, project_id, node_id):
        instruction = request.data.get('instruction', '')
        if not instruction:
            return Response({"error": "需要提供修改指令"}, status=400)
            
        try:
            from memory import pyramid
            node, new_text, diffs = pyramid.edit_node_partial(project_id, node_id, instruction)
            return Response({
                "id": node.id,
                "version": node.version,
                "new_content": new_text,
                "diffs": diffs,
                "applied_changes": len(diffs)
            })
        except Exception as e:
            return Response({"error": str(e)}, status=500)


class IngestView(APIView):
    def post(self, request, project_id):
        text = request.data.get('text', '')
        title = request.data.get('title', '')
        parent_id = request.data.get('parent_id')
        node_type = request.data.get('node_type', 'narrative')
        chapter_index = int(request.data.get('chapter_index', 0))
        if not text:
            return Response({"error": "需要提供文本"}, status=400)
        nodes = pyramid.ingest_text(project_id, text, title, parent_id, node_type, chapter_index=chapter_index)
        return Response({"ingested": len(nodes), "node_ids": [n.id for n in nodes]})


class ConsolidateView(APIView):
    def post(self, request, project_id):
        target = request.data.get('target', 'universe')
        node_id = request.data.get('node_id')
        if target == 'universe':
            node = pyramid.consolidate_universe(project_id)
        elif target == 'arc' and node_id:
            node = pyramid.consolidate_arc(project_id, node_id)
        elif target == 'chapter' and node_id:
            node = pyramid.consolidate_chapter(project_id, node_id)
        else:
            return Response({"error": "无效目标"}, status=400)
        return Response({"id": node.id, "title": node.title, "summary": node.summary[:500]})


class RetrieveView(APIView):
    def post(self, request, project_id):
        query = request.data.get('query', '')
        max_tokens = int(request.data.get('max_tokens', 150000))
        if not query:
            return Response({"error": "需要提供查询"}, status=400)
        context = pyramid.retrieve_context(project_id, query, max_tokens)
        return Response({"context": context, "chars": len(context), "estimated_tokens": len(context) // 2})


class RetrieveEvolutionView(APIView):
    def post(self, request, project_id):
        query = request.data.get('query', '')
        entity = request.data.get('entity', '')
        context = pyramid.retrieve_evolution_context(project_id, query, entity)
        return Response({"context": context, "chars": len(context)})


class CharacterListView(APIView):
    def get(self, request, project_id):
        chars = Character.objects.filter(project_id=project_id)
        return Response([{
            'id': c.id, 'name': c.name, 'aliases': c.aliases,
            'description': c.description[:300], 'traits': c.traits,
            'current_state': c.current_state[:200] if c.current_state else '',
            'snapshot_count': c.snapshots.count(),
            'created_at': c.created_at.isoformat(),
        } for c in chars])

    def post(self, request, project_id):
        data = request.data
        char, created = Character.objects.get_or_create(
            project_id=project_id, name=data['name'],
            defaults={
                'description': data.get('description', ''),
                'traits': data.get('traits', []),
                'aliases': data.get('aliases', []),
                'backstory': data.get('backstory', ''),
                'current_state': data.get('current_state', ''),
            }
        )
        return Response({'id': char.id, 'name': char.name, 'created': created})


class CharacterDetailView(APIView):
    def get(self, request, char_id):
        try:
            c = Character.objects.get(id=char_id)
        except Character.DoesNotExist:
            return Response({"error": "未找到"}, status=404)
        snapshots = CharacterSnapshot.objects.filter(character=c).order_by('chapter_index')
        return Response({
            'id': c.id, 'name': c.name, 'aliases': c.aliases,
            'description': c.description, 'traits': c.traits,
            'backstory': c.backstory, 'current_state': c.current_state,
            'snapshots': [{
                'id': s.id, 'chapter_index': s.chapter_index,
                'state': s.state, 'traits': s.traits,
                'beliefs': s.beliefs, 'goals': s.goals,
                'relationships': s.relationships,
                'change_description': s.change_description,
                'created_at': s.created_at.isoformat(),
            } for s in snapshots],
        })


class ExtractCharactersView(APIView):
    def post(self, request, project_id):
        text = request.data.get('text', '')
        chapter_index = int(request.data.get('chapter_index', 0))
        if not text:
            return Response({"error": "需要提供文本"}, status=400)
        chars = pyramid.extract_characters(project_id, text, chapter_index)
        return Response([{'id': c.id, 'name': c.name, 'description': c.description[:200]} for c in chars])


class TimelineView(APIView):
    def get(self, request, project_id):
        event_type = request.query_params.get('type')
        qs = TimelineEvent.objects.filter(project_id=project_id)
        if event_type:
            qs = qs.filter(event_type=event_type)
        return Response([{
            'id': e.id, 'event_type': e.event_type,
            'event_type_display': e.get_event_type_display(),
            'chapter_index': e.chapter_index,
            'story_time': e.story_time, 'title': e.title,
            'description': e.description,
            'characters_involved': e.characters_involved,
            'impact': e.impact,
            'created_at': e.created_at.isoformat(),
        } for e in qs])

    def post(self, request, project_id):
        d = request.data
        event = TimelineEvent.objects.create(
            project_id=project_id,
            event_type=d.get('event_type', 'plot'),
            chapter_index=int(d.get('chapter_index', 0)),
            story_time=d.get('story_time', ''),
            title=d['title'],
            description=d.get('description', ''),
            characters_involved=d.get('characters_involved', []),
            impact=d.get('impact', ''),
        )
        return Response({'id': event.id}, status=201)
