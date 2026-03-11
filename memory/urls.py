from django.urls import path
from memory.views import (
    PyramidStatsView, PyramidTreeView, MemoryNodeListView, MemoryNodeDetailView,
    MemoryNodeEditAgentView,
    IngestView, ConsolidateView, RetrieveView, RetrieveEvolutionView,
    CharacterListView, CharacterDetailView, ExtractCharactersView, TimelineView
)

urlpatterns = [
    path('<int:project_id>/stats/', PyramidStatsView.as_view()),
    path('<int:project_id>/tree/', PyramidTreeView.as_view()),
    path('<int:project_id>/nodes/', MemoryNodeListView.as_view()),
    path('node/<int:node_id>/', MemoryNodeDetailView.as_view()),
    path('<int:project_id>/node/<int:node_id>/agent_edit/', MemoryNodeEditAgentView.as_view()),
    path('<int:project_id>/ingest/', IngestView.as_view()),
    path('<int:project_id>/consolidate/', ConsolidateView.as_view()),
    path('<int:project_id>/retrieve/', RetrieveView.as_view()),
    path('<int:project_id>/retrieve-evolution/', RetrieveEvolutionView.as_view()),
    path('<int:project_id>/characters/', CharacterListView.as_view()),
    path('character/<int:char_id>/', CharacterDetailView.as_view()),
    path('<int:project_id>/extract-characters/', ExtractCharactersView.as_view()),
    path('<int:project_id>/timeline/', TimelineView.as_view()),
]
