from django.contrib import admin
from .models import App


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'icon', 'is_active', 'order']
    list_editable = ['is_active', 'order']
    prepopulated_fields = {'slug': ('name',)}
