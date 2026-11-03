from django.contrib import admin
from .models import StaffNotificationPreference, NotificationDeliveryLog

@admin.register(StaffNotificationPreference)
class StaffNotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('staff_user', 'email_enabled', 'daily_digest', 'notify_critical_trends', 'notify_emergency_urgency')
    list_filter = ('email_enabled', 'daily_digest', 'notify_critical_trends')

@admin.register(NotificationDeliveryLog)
class NotificationDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'subject', 'status', 'retry_count', 'sent_at')
    list_filter = ('status',)
    search_fields = ('recipient__email', 'subject')
