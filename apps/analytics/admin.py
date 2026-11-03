from django.contrib import admin
from .models import TrendAlert

@admin.register(TrendAlert)
class TrendAlertAdmin(admin.ModelAdmin):
    list_display = ('alert_title', 'department', 'location', 'severity', 'current_volume', 'baseline_volume', 'spike_ratio', 'is_acknowledged', 'created_at')
    list_filter = ('severity', 'is_acknowledged', 'department')
    search_fields = ('alert_title',)
