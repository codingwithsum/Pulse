from django.db import models
from django.contrib.auth.models import User
from apps.core.models import TimeStampedModel
from apps.feedback.models import FeedbackItem
from apps.master_data.models import Department, CivicCategory, CivicLocation

class FeedbackAnalysis(TimeStampedModel):
    """
    Stores structured AI inference results for a feedback item.
    Separated from FeedbackItem to allow re-analysis across model versions.
    """
    SENTIMENT_CHOICES = [
        ('POSITIVE', 'Positive'),
        ('NEGATIVE', 'Negative'),
        ('NEUTRAL', 'Neutral'),
        ('MIXED', 'Mixed'),
        ('UNCERTAIN', 'Uncertain'),
    ]

    URGENCY_CHOICES = [
        ('EMERGENCY', '🚨 Emergency / Critical Hazard'),
        ('HIGH', '⚠️ High Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('LOW', 'Low Priority / Routine'),
    ]

    feedback_item = models.ForeignKey(FeedbackItem, on_delete=models.CASCADE, related_name='analyses')
    model_version = models.CharField(max_length=60, help_text="Identifier of the analyzer engine used")
    is_civic_related = models.BooleanField(default=True, db_index=True)
    sentiment = models.CharField(max_length=20, choices=SENTIMENT_CHOICES, db_index=True)
    sentiment_score = models.FloatField(help_text="Polarity index from -1.0 (most negative) to +1.0 (most positive)")
    category = models.ForeignKey(CivicCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='analyses')
    suggested_department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='suggested_analyses')
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default='MEDIUM', db_index=True)
    urgency_reasoning = models.TextField(blank=True, help_text="Evidence-backed reasoning for urgency flag")
    extracted_location = models.ForeignKey(CivicLocation, null=True, blank=True, on_delete=models.SET_NULL, related_name='matched_analyses')
    raw_location_string = models.CharField(max_length=255, blank=True, help_text="Exact landmark/area phrase extracted from text")
    recurring_theme = models.CharField(max_length=150, blank=True, help_text="Normalized issue cluster")
    short_summary = models.CharField(max_length=255, blank=True)
    confidence_score = models.FloatField(default=0.0, help_text="Estimated classification confidence (0.0 - 1.0)")
    requires_human_review = models.BooleanField(default=False, db_index=True)
    is_active_version = models.BooleanField(default=True, db_index=True)
    raw_response = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback Analysis'
        verbose_name_plural = 'Feedback Analyses'
        indexes = [
            models.Index(fields=['suggested_department', 'created_at']),
            models.Index(fields=['category', 'created_at']),
        ]

    def __str__(self):
        return f"Analysis for {str(self.feedback_item.id)[:8]} ({self.sentiment}, {self.urgency})"


class AnalysisReview(TimeStampedModel):
    """
    Audit log of human-in-the-loop corrections made by municipal staff.
    """
    analysis = models.ForeignKey(FeedbackAnalysis, on_delete=models.CASCADE, related_name='reviews')
    reviewed_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name='conducted_reviews')
    previous_category = models.ForeignKey(CivicCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    corrected_category = models.ForeignKey(CivicCategory, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    previous_department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    corrected_department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    previous_urgency = models.CharField(max_length=20, blank=True)
    corrected_urgency = models.CharField(max_length=20, blank=True)
    review_notes = models.TextField(blank=True, help_text="Internal staff notes, action taken, or flying squad dispatch details")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Analysis Review / Correction'
        verbose_name_plural = 'Analysis Reviews / Corrections'

    def __str__(self):
        return f"Review by {self.reviewed_by.username} on Analysis #{self.analysis_id}"
