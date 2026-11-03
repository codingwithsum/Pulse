from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel
from apps.master_data.models import Department, CivicLocation
from apps.analytics.models import TrendAlert

class StaffNotificationPreference(TimeStampedModel):
    """
    Opt-in notification rules for authorized municipal personnel.
    Strictly municipal staff only; never citizens.
    """
    staff_user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='notification_preference')
    email_enabled = models.BooleanField(default=False, help_text="Master toggle for outbound emails")
    daily_digest = models.BooleanField(default=True, help_text="Daily morning summary digest at 08:00 AM")
    notify_critical_trends = models.BooleanField(default=True, help_text="Immediate alert on critical volume spikes")
    notify_emergency_urgency = models.BooleanField(default=False, help_text="Immediate alert on safety hazards")
    filter_department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional: Restrict notifications to one department"
    )
    filter_ward = models.ForeignKey(
        CivicLocation,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Optional: Restrict notifications to one ward"
    )

    class Meta:
        verbose_name = 'Staff Notification Preference'
        verbose_name_plural = 'Staff Notification Preferences'

    def __str__(self):
        return f"Notification Prefs: {self.staff_user.username}"


class NotificationDeliveryLog(TimeStampedModel):
    """
    Audit record ensuring email delivery idempotency and retry tracking.
    """
    STATUS_CHOICES = [
        ('QUEUED', 'Queued for Delivery'),
        ('SENT', 'Sent Successfully'),
        ('FAILED', 'Failed / Exhausted Retries'),
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_notifications')
    alert = models.ForeignKey(TrendAlert, null=True, blank=True, on_delete=models.SET_NULL, related_name='delivery_logs')
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='QUEUED', db_index=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification Delivery Log'
        verbose_name_plural = 'Notification Delivery Logs'

    def __str__(self):
        return f"Notification to {self.recipient.email} ({self.status})"
