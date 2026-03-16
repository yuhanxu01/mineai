from django.contrib import admin
from .models import CodeProject, CodeFile, FileVersion, CodeSession, CodeMessage

@admin.register(CodeProject)
class CodeProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'language', 'user', 'created_at')
    list_filter = ('language',)

@admin.register(CodeFile)
class CodeFileAdmin(admin.ModelAdmin):
    list_display = ('path', 'project', 'language', 'size', 'updated_at')

@admin.register(FileVersion)
class FileVersionAdmin(admin.ModelAdmin):
    list_display = ('file', 'version', 'change_summary', 'created_at')

@admin.register(CodeSession)
class CodeSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'created_at')

@admin.register(CodeMessage)
class CodeMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'role', 'created_at')
