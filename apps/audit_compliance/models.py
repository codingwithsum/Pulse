from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    """
    Immutable audit trail recording security-sensitive municipal staff actions,
    such as human-in-the-loop reclassifications, file uploads, and credential adjustments.
    """
    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_entries')
    action = models.CharField(max_length=60, db_index=True, help_text="e.g. CLASSIFICATION_OVERRIDE, IMPORT_CSV, UPDATE_CONFIG")
    target_model = models.CharField(max_length=60, help_text="Target entity class (e.g. FeedbackAnalysis)")
    target_id = models.CharField(max_length=100, help_text="ID or UUID of the target record")
    details = models.JSONField(default=dict, blank=True, help_text="Structured before/after diff or contextual event details")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user_str = self.user.username if self.user else "System"
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {user_str}: {self.action} on {self.target_model}:{self.target_id}"
