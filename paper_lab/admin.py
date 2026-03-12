from django.contrib import admin
from .models import (
    ResearchProject, Literature, LiteratureChunk,
    ResearchNote, ResearchConversation, ResearchMessage,
    ResearchIdea, WritingDraft,
)

admin.site.register(ResearchProject)
admin.site.register(Literature)
admin.site.register(LiteratureChunk)
admin.site.register(ResearchNote)
admin.site.register(ResearchConversation)
admin.site.register(ResearchMessage)
admin.site.register(ResearchIdea)
admin.site.register(WritingDraft)
