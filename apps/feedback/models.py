import uuid
from django.db import models
from apps.core.models import TimeStampedModel
from apps.ingestion.models import DataSource, ImportRun

class FeedbackItem(TimeStampedModel):
    """
    The canonical, immutable record of normalized civic feedback across all intake channels.
    Strictly free of citizen names, phone numbers, or private credentials.
    Now includes Resource-wise Complaint Source Tracking (Social Media, Via Email, Official Website).
    """
    STATUS_CHOICES = [
        ('PENDING_ANALYSIS', 'Pending AI Analysis'),
        ('ANALYZED', 'AI Analyzed'),
        ('REVIEWED', 'Human Review Completed'),
        ('DISCARDED', 'Discarded (Non-Civic / Spam)'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('SOCIAL_MEDIA', 'Social Media'),
        ('EMAIL', 'Via Email'),
        ('OFFICIAL_WEBSITE', 'Official Website'),
        ('OTHER', 'Other / Direct'),
    ]

    SOURCE_PLATFORM_CHOICES = [
        ('TWITTER', 'Twitter (X)'),
        ('FACEBOOK', 'Facebook'),
        ('GMAIL', 'Gmail'),
        ('RMC_PORTAL', 'RMC Portal'),
        ('WHATSAPP', 'WhatsApp'),
        ('FILE_IMPORT', 'Batch Import'),
        ('OTHER', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name='feedback_items')
    import_run = models.ForeignKey(ImportRun, null=True, blank=True, on_delete=models.SET_NULL, related_name='feedback_items')
    external_id = models.CharField(max_length=255, blank=True, help_text="Channel-specific original ID (e.g. WhatsApp message ID)")
    content_hash = models.CharField(max_length=64, db_index=True, help_text="SHA-256 hash of normalized text to block duplicate ingestion")
    raw_text = models.TextField(help_text="Citizen text preserving Gujarati, Hindi, or English verbatim")
    detected_language = models.CharField(max_length=10, default='und', db_index=True, help_text="gu, hi, en, mixed, und")
    published_at = models.DateTimeField(db_index=True, help_text="Original timestamp from source channel")
    raw_metadata = models.JSONField(default=dict, blank=True, help_text="Permitted technical metadata; strictly PII-free")
    is_synthetic = models.BooleanField(default=False, db_index=True, help_text="Flags mock/demo records explicitly")
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='PENDING_ANALYSIS', db_index=True)

    # Resource-wise Complaint Tracking
    source_type = models.CharField(
        max_length=50,
        choices=SOURCE_TYPE_CHOICES,
        default='OTHER',
        db_index=True,
        help_text="Tracked complaint source resource (Social Media, Via Email, Official Website)"
    )
    source_platform = models.CharField(
        max_length=50,
        choices=SOURCE_PLATFORM_CHOICES,
        default='OTHER',
        db_index=True,
        help_text="Original platform (Twitter (X), Facebook, Gmail, RMC Portal)"
    )

    class Meta:
        ordering = ['-published_at']
        verbose_name = 'Civic Feedback Item'
        verbose_name_plural = 'Civic Feedback Items'
        indexes = [
            models.Index(fields=['data_source', 'external_id']),
            models.Index(fields=['content_hash', 'published_at']),
            models.Index(fields=['source_type', 'source_platform']),
        ]

    def __str__(self):
        return f"Feedback {str(self.id)[:8]} ({self.get_source_type_display()} - {self.get_source_platform_display()})"

    def detect_source(self):
        """
        Automatically identifies the original complaint source and platform without asking citizens.
        Normalizes:
        - Twitter complaint → Social Media → Twitter (X)
        - Facebook complaint → Social Media → Facebook
        - Incoming email complaint → Via Email → Gmail
        - Website form complaint → Official Website → RMC Portal
        """
        st = (self.source_type or "").strip()
        sp = (self.source_platform or "").strip()

        # If already set to valid canonical values (and not OTHER), keep and normalize
        type_norm_map = {
            'social media': 'SOCIAL_MEDIA',
            'social': 'SOCIAL_MEDIA',
            'social_media': 'SOCIAL_MEDIA',
            'via email': 'EMAIL',
            'email': 'EMAIL',
            'gmail': 'EMAIL',
            'official website': 'OFFICIAL_WEBSITE',
            'official_website': 'OFFICIAL_WEBSITE',
            'website': 'OFFICIAL_WEBSITE',
            'portal': 'OFFICIAL_WEBSITE',
            'rmc portal': 'OFFICIAL_WEBSITE',
        }
        plat_norm_map = {
            'twitter (x)': 'TWITTER',
            'twitter': 'TWITTER',
            'twitter_x': 'TWITTER',
            'x': 'TWITTER',
            'facebook': 'FACEBOOK',
            'fb': 'FACEBOOK',
            'meta': 'FACEBOOK',
            'gmail': 'GMAIL',
            'email': 'GMAIL',
            'rmc portal': 'RMC_PORTAL',
            'rmc_portal': 'RMC_PORTAL',
            'portal': 'RMC_PORTAL',
            'whatsapp': 'WHATSAPP',
            'file_import': 'FILE_IMPORT',
        }

        if st.lower() in type_norm_map:
            st = type_norm_map[st.lower()]
        if sp.lower() in plat_norm_map:
            sp = plat_norm_map[sp.lower()]

        meta = self.raw_metadata or {}
        channel_hint = str(
            meta.get("channel") or meta.get("source") or meta.get("source_platform") or
            meta.get("platform") or meta.get("intake_source") or ""
        ).lower()
        ext = (self.external_id or "").lower()
        ds_type = (self.data_source.source_type if self.data_source else "").upper()
        ds_name = (self.data_source.name if self.data_source else "").lower()

        # 1. Twitter (X)
        if (
            sp == 'TWITTER'
            or 'twitter' in channel_hint or channel_hint in ('tw', 'x')
            or ext.startswith(('tw-', 'twitter-', 'x-'))
            or ds_type == 'TWITTER_X' or 'twitter' in ds_name
        ):
            self.source_type = 'SOCIAL_MEDIA'
            self.source_platform = 'TWITTER'
            return

        # 2. Facebook
        if (
            sp == 'FACEBOOK'
            or 'facebook' in channel_hint or channel_hint in ('fb', 'meta')
            or ext.startswith(('fb-', 'facebook-', 'meta-'))
            or ds_type == 'FACEBOOK' or 'facebook' in ds_name
        ):
            self.source_type = 'SOCIAL_MEDIA'
            self.source_platform = 'FACEBOOK'
            return

        # 3. Via Email: Gmail / authorized incoming email account
        if (
            sp == 'GMAIL' or st == 'EMAIL'
            or 'gmail' in channel_hint or 'email' in channel_hint or 'mail' in channel_hint
            or ext.startswith(('email-', 'gmail-', 'mail-'))
            or ds_type == 'EMAIL' or 'email' in ds_name or 'gmail' in ds_name
        ):
            self.source_type = 'EMAIL'
            self.source_platform = 'GMAIL'
            return

        # 4. Official Website: RMC complaint submission portal
        if (
            sp == 'RMC_PORTAL' or st == 'OFFICIAL_WEBSITE'
            or 'portal' in channel_hint or 'website' in channel_hint or 'web' in channel_hint
            or ext.startswith(('rmc-', 'portal-', 'web-', 'webform-'))
            or ds_type in ('RMC_PORTAL', 'OFFICIAL_WEBSITE')
            or 'portal' in ds_name or 'website' in ds_name
        ):
            self.source_type = 'OFFICIAL_WEBSITE'
            self.source_platform = 'RMC_PORTAL'
            return

        # 5. WhatsApp (categorized under Social Media intake)
        if (
            sp == 'WHATSAPP'
            or 'whatsapp' in channel_hint or ext.startswith('wa-')
            or ds_type == 'WHATSAPP' or 'whatsapp' in ds_name
        ):
            self.source_type = 'SOCIAL_MEDIA'
            self.source_platform = 'WHATSAPP'
            return

        # 6. Fallback if still unset or OTHER
        if st in dict(self.SOURCE_TYPE_CHOICES) and st != 'OTHER':
            self.source_type = st
        else:
            self.source_type = 'OFFICIAL_WEBSITE'

        if sp in dict(self.SOURCE_PLATFORM_CHOICES) and sp != 'OTHER':
            self.source_platform = sp
        else:
            self.source_platform = 'RMC_PORTAL'

    def save(self, *args, **kwargs):
        from django.utils import timezone
        if not self.published_at:
            self.published_at = timezone.now()
        if not self.source_type or not self.source_platform or self.source_type == 'OTHER' or self.source_platform == 'OTHER':
            self.detect_source()
        super().save(*args, **kwargs)
