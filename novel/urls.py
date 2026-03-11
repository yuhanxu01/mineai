from django.urls import path
from novel.views import (
    ProjectListView, ProjectDetailView, ChapterDetailView, ChapterCreateView,
    WriteChapterView, ContinueWritingView, ChatView, GenerateOutlineView,
    ConsolidateProjectView, GenerateIdeaView,
    WriteChapterStreamView, ContinueWritingStreamView,
)

urlpatterns = [
    path('projects/', ProjectListView.as_view()),
    path('project/<int:project_id>/', ProjectDetailView.as_view()),
    path('project/<int:project_id>/chapters/', ChapterCreateView.as_view()),
    path('chapter/<int:chapter_id>/', ChapterDetailView.as_view()),
    path('chapter/<int:chapter_id>/write/', WriteChapterView.as_view()),
    path('chapter/<int:chapter_id>/write-stream/', WriteChapterStreamView.as_view()),
    path('chapter/<int:chapter_id>/continue/', ContinueWritingView.as_view()),
    path('chapter/<int:chapter_id>/continue-stream/', ContinueWritingStreamView.as_view()),
    path('project/<int:project_id>/chat/', ChatView.as_view()),
    path('project/<int:project_id>/outline/', GenerateOutlineView.as_view()),
    path('project/<int:project_id>/consolidate/', ConsolidateProjectView.as_view()),
    path('generate-idea/', GenerateIdeaView.as_view()),
]
