from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel
from apps.master_data.models import Department, CivicCategory, CivicLocation

class TrendAlert(TimeStampedModel):
    """
    Flags statistically significant spikes or recurring civic anomalies
    calculated from stored feedback records over sliding time windows.
    """
    SEVERITY_CHOICES = [
        ('CRITICAL', '🚨 Critical Spike (Volume >= 3.0x Baseline)'),
        ('WARNING', '⚠️ Warning Anomaly (Volume >= 2.0x Baseline)'),
        ('ADVISORY', 'ℹ️ Advisory Pattern (Emerging Multi-Ward Topic)'),
    ]

    alert_title = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='trend_alerts')
    category = models.ForeignKey(CivicCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='trend_alerts')
    location = models.ForeignKey(CivicLocation, null=True, blank=True, on_delete=models.SET_NULL, related_name='trend_alerts')
    time_window_start = models.DateTimeField()
    time_window_end = models.DateTimeField()
    baseline_volume = models.FloatField(help_text="Expected feedback count for window based on 7-day baseline")
    current_volume = models.PositiveIntegerField(help_text="Observed complaint count in active window")
    spike_ratio = models.FloatField(help_text="Observed volume divided by baseline volume (e.g. 3.42x)")
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='WARNING', db_index=True)
    sample_evidence_ids = models.JSONField(default=list, blank=True, help_text="UUIDs of representative FeedbackItems")
    is_acknowledged = models.BooleanField(default=False, db_index=True)
    acknowledged_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trend Alert'
        verbose_name_plural = 'Trend Alerts'
        indexes = [
            models.Index(fields=['department', 'is_acknowledged']),
        ]

    def __str__(self):
        return f"{self.alert_title} ({self.get_severity_display()})"
