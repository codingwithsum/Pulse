from typing import Optional
from apps.feedback.models import FeedbackItem
from apps.intelligence.models import FeedbackAnalysis, AnalysisReview
from apps.master_data.models import Department, CivicCategory, CivicLocation
from .analyzers.local_rules import LocalCivicAnalyzer
from .analyzers.base import BaseCivicAnalyzer

# Default analyzer singleton
_default_analyzer = LocalCivicAnalyzer()

def official_ward_number(metadata: Optional[dict]) -> Optional[int]:
    """Ward recorded by RMC itself (official complaint exports carry a Ward column); None if absent or invalid."""
    try:
        number = int(str((metadata or {}).get("rmc_ward", "")).strip())
    except ValueError:
        return None
    return number if 1 <= number <= 18 else None


def get_analyzer(model_version: Optional[str] = None) -> BaseCivicAnalyzer:
    """Returns the configured analyzer engine."""
    return _default_analyzer

def analyze_and_store_feedback(feedback_item: FeedbackItem, analyzer: Optional[BaseCivicAnalyzer] = None) -> FeedbackAnalysis:
    """
    Executes multilingual analysis on a FeedbackItem, maps foreign keys to official RMC master data,
    and saves the FeedbackAnalysis record.
    """
    if analyzer is None:
        analyzer = get_analyzer()

    result = analyzer.analyze(feedback_item.raw_text, metadata=feedback_item.raw_metadata)

    # 1. Map Department
    dept = None
    if result.department_code:
        dept = Department.objects.filter(code=result.department_code).first()
        if not dept:
            # Fallback search by name
            dept = Department.objects.filter(name__icontains=result.department_code.replace("-", " ")).first()

    # 2. Map Category
    category = None
    if result.category_code and dept:
        category = CivicCategory.objects.filter(department=dept, code=result.category_code).first()
        if not category:
            category = CivicCategory.objects.filter(department=dept).first()

    # 3. Map Location
    # The ward in RMC's own record is authoritative; text matching is only the fallback.
    ward_number = official_ward_number(feedback_item.raw_metadata) or result.suggested_ward_number
    location = CivicLocation.objects.filter(ward_number=ward_number).first() if ward_number else None

    # 4. Mark previous active analyses as inactive
    FeedbackAnalysis.objects.filter(feedback_item=feedback_item).update(is_active_version=False)

    # 5. Create new analysis
    analysis = FeedbackAnalysis.objects.create(
        feedback_item=feedback_item,
        model_version=result.model_version,
        is_civic_related=result.is_civic_related,
        sentiment=result.sentiment,
        sentiment_score=result.sentiment_score,
        category=category,
        suggested_department=dept,
        urgency=result.urgency,
        urgency_reasoning=result.urgency_reasoning,
        extracted_location=location,
        raw_location_string=result.extracted_location_name or "",
        recurring_theme=result.recurring_theme,
        short_summary=result.short_summary,
        confidence_score=result.confidence_score,
        requires_human_review=result.requires_human_review,
        is_active_version=True,
        raw_response=result.raw_response,
    )

    # Update item status
    feedback_item.status = "ANALYZED"
    feedback_item.detected_language = result.detected_language
    feedback_item.save(update_fields=["status", "detected_language", "updated_at"])

    return analysis
