from django.contrib import admin

# Register your models here.
# admin.py
from django.contrib import admin
from .models import Album, Photo

@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('title', 'created_by__username')
    list_editable = ('status',)   # 👈 Checkbox / dropdown approval
