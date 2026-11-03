from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'target_model', 'target_id', 'ip_address')
    list_filter = ('action', 'target_model')
    search_fields = ('action', 'target_id', 'details')
    readonly_fields = ('timestamp', 'user', 'action', 'target_model', 'target_id', 'details', 'ip_address')
