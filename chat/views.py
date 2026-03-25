import json
from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import ModelSerializer
from .models import Conversation, Message
from core.llm import chat_stream, _get_config

class MessageSerializer(ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'role', 'content', 'created_at']

class ConversationSerializer(ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'model_name', 'created_at', 'updated_at', 'messages']

class ConversationListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # 20 limit handled in Conversation.save()
        serializer.save(user=self.request.user)

class ConversationDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)
        
    def perform_destroy(self, instance):
        instance.delete()

class ChatStreamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        conv = get_object_or_404(Conversation, pk=pk, user=request.user)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Message content cannot be empty'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Optional: Allow user to switch model manually
        model_name = request.data.get('model_name')
        if model_name and model_name in ['glm-4.7-flash', 'glm-4.5-flash']:
            conv.model_name = model_name
            conv.save()
            
        # Save user message
        user_msg = Message.objects.create(conversation=conv, role='user', content=content)
        
        # Build message history for LLM
        history = []
        for msg in conv.messages.all().order_by('created_at'):
            history.append({"role": msg.role, "content": msg.content})
            
        system_prompt = "You are a helpful AI assistant. Please format your reply using Markdown."
        
        try:
            config = _get_config()
            # override config model name for the single request
            original_model = config.chat_model
            config.chat_model = conv.model_name
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
            
        user_id = request.user.id

        def stream_generator():
            full_response = ""
            try:
                for chunk in chat_stream(history, system=system_prompt, config=config, user_id=user_id):
                    if chunk:
                        full_response += chunk
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk})}\n\n"
                        
                # After done, save assistant message
                Message.objects.create(conversation=conv, role='assistant', content=full_response)
                # Auto-generate title for conversation if it's the first message
                if conv.title == 'New Chat' and len(history) <= 2:
                    # just take first 20 chars of user prompt as title
                    conv.title = content[:20] + ('...' if len(content) > 20 else '')
                    conv.save()
                    
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'text': str(e)})}\n\n"

        response = StreamingHttpResponse(stream_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response
