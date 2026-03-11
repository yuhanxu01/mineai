from django.contrib import admin
from memory.models import (
    MemoryNode, MemorySnapshot, MemoryLink, Character,
    CharacterSnapshot, CharacterRelation, TimelineEvent
)

admin.site.register(MemoryNode)
admin.site.register(MemorySnapshot)
admin.site.register(MemoryLink)
admin.site.register(Character)
admin.site.register(CharacterSnapshot)
admin.site.register(CharacterRelation)
admin.site.register(TimelineEvent)
