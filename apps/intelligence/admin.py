from django.contrib import admin
from .models import FeedbackAnalysis, AnalysisReview

@admin.register(FeedbackAnalysis)
class FeedbackAnalysisAdmin(admin.ModelAdmin):
    list_display = ('id', 'feedback_short', 'sentiment', 'urgency', 'category', 'suggested_department', 'confidence_score', 'requires_human_review')
    list_filter = ('sentiment', 'urgency', 'suggested_department', 'requires_human_review', 'model_version')
    search_fields = ('feedback_item__raw_text', 'urgency_reasoning', 'recurring_theme')

    def feedback_short(self, obj):
        return str(obj.feedback_item.id)[:8]
    feedback_short.short_description = 'Feedback UUID'

@admin.register(AnalysisReview)
class AnalysisReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'analysis', 'reviewed_by', 'corrected_department', 'corrected_urgency', 'created_at')
    list_filter = ('corrected_department', 'corrected_urgency', 'reviewed_by')
    search_fields = ('review_notes',)
