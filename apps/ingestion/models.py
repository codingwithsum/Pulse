from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel

class DataSource(TimeStampedModel):
    """
    Registry of external ingestion channels and intake connectors.
    """
    SOURCE_TYPE_CHOICES = [
        ('FILE_IMPORT', 'CSV / Excel Batch Importer'),
        ('WHATSAPP', 'WhatsApp Business Cloud API'),
        ('TWITTER_X', 'Twitter / X (Official API v2)'),
        ('FACEBOOK', 'Meta / Facebook Page Feed'),
        ('INSTAGRAM', 'Meta / Instagram Feed'),
        ('RMC_PORTAL', 'RMC Grievance Portal (e-Gov Gateway)'),
        ('EMAIL', 'Gmail / Authorized Incoming Email'),
        ('OFFICIAL_WEBSITE', 'Official Website Complaint Portal'),
    ]

    HEALTH_STATUS_CHOICES = [
        ('HEALTHY', 'Healthy / Connected'),
        ('DEGRADED', 'Degraded / Rate Limited'),
        ('DISCONNECTED', 'Disconnected / Error'),
        ('PENDING_CONFIG', 'Pending Credentials / Scaffolding'),
    ]

    name = models.CharField(max_length=150, unique=True)
    source_type = models.CharField(max_length=30, choices=SOURCE_TYPE_CHOICES, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    health_status = models.CharField(max_length=20, choices=HEALTH_STATUS_CHOICES, default='PENDING_CONFIG')
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Data Source'
        verbose_name_plural = 'Data Sources'

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"


class ConnectorConfig(TimeStampedModel):
    """
    Secure configuration and credentials for an intake connector.
    Kept strictly decoupled from ordinary public metadata.
    """
    data_source = models.OneToOneField(DataSource, on_delete=models.CASCADE, related_name='config')
    api_endpoint = models.CharField(max_length=255, blank=True)
    webhook_verify_token = models.CharField(max_length=255, blank=True)
    encrypted_credentials = models.TextField(
        blank=True,
        help_text="Secure credentials / tokens; never exposed through REST API responses"
    )
    settings_json = models.JSONField(
        default=dict,
        blank=True,
        help_text="Non-secret connector settings (batch size, sync frequency)"
    )

    class Meta:
        verbose_name = 'Connector Configuration'
        verbose_name_plural = 'Connector Configurations'

    def __str__(self):
        return f"Config: {self.data_source.name}"


class ImportRun(TimeStampedModel):
    """
    Audit record for batch spreadsheet uploads or historical sync executions.
    """
    STATUS_CHOICES = [
        ('PENDING', 'Pending Execution'),
        ('PROCESSING', 'Processing Rows'),
        ('COMPLETED', 'Completed Successfully'),
        ('FAILED', 'Failed with Errors'),
    ]

    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, related_name='import_runs')
    uploaded_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='uploaded_runs')
    file_name = models.CharField(max_length=255)
    total_rows = models.PositiveIntegerField(default=0)
    imported_rows = models.PositiveIntegerField(default=0)
    duplicate_rows = models.PositiveIntegerField(default=0)
    error_rows = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', db_index=True)
    error_log = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Import Run'
        verbose_name_plural = 'Import Runs'

    def __str__(self):
        return f"Run #{self.id} - {self.file_name} ({self.status})"
