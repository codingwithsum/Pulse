from django.contrib import admin
from .models import FeedbackItem

@admin.register(FeedbackItem)
class FeedbackItemAdmin(admin.ModelAdmin):
    list_display = (
        'id_short', 'source_type', 'source_platform', 'status',
        'detected_language', 'is_synthetic', 'published_at'
    )
    list_filter = (
        'source_type', 'source_platform', 'status',
        'data_source', 'detected_language', 'is_synthetic'
    )
    search_fields = ('raw_text', 'external_id', 'content_hash')
    readonly_fields = ('id', 'content_hash', 'created_at')

    def id_short(self, obj):
        return str(obj.id)[:8]
    id_short.short_description = 'Complaint ID'
