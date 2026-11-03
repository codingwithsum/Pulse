import logging
from typing import Optional

from django.conf import settings

from apps.feedback.models import FeedbackItem
from apps.intelligence.models import FeedbackAnalysis, AnalysisReview
from apps.master_data.models import Department, CivicCategory, CivicLocation
from .analyzers.local_rules import LocalCivicAnalyzer
from .analyzers.base import BaseCivicAnalyzer

logger = logging.getLogger(__name__)

# Cached analyzer singleton (resolved once on first call)
_default_analyzer: Optional[BaseCivicAnalyzer] = None


def official_ward_number(metadata: Optional[dict]) -> Optional[int]:
    """Ward recorded by RMC itself (official complaint exports carry a Ward column); None if absent or invalid."""
    try:
        number = int(str((metadata or {}).get("rmc_ward", "")).strip())
    except ValueError:
        return None
    return number if 1 <= number <= 18 else None


def get_analyzer(model_version: Optional[str] = None) -> BaseCivicAnalyzer:
    """
    Returns the best available analyzer engine.

    Priority:
      1. OllamaCivicAnalyzer  — if OLLAMA_MODEL is set in settings AND Ollama server is reachable
      2. LocalCivicAnalyzer   — deterministic offline fallback (always works)

    To enable Ollama, add to settings.py (or .env):
        OLLAMA_MODEL    = "llama3.2"
        OLLAMA_BASE_URL = "http://localhost:11434"   # optional, this is the default
    """
    global _default_analyzer

    if _default_analyzer is not None:
        return _default_analyzer

    ollama_model   = getattr(settings, "OLLAMA_MODEL", None)
    ollama_base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")

    if ollama_model:
        try:
            from .analyzers.ollama_analyzer import OllamaCivicAnalyzer, is_ollama_available
            if is_ollama_available(ollama_base_url):
                _default_analyzer = OllamaCivicAnalyzer(
                    model=ollama_model,
                    base_url=ollama_base_url,
                )
                logger.info(
                    f"[PULSE] Ollama analyzer activated — model: {ollama_model} @ {ollama_base_url}"
                )
                return _default_analyzer
            else:
                logger.warning(
                    f"[PULSE] OLLAMA_MODEL='{ollama_model}' is set but Ollama is not reachable "
                    f"at {ollama_base_url}. Falling back to LocalCivicAnalyzer."
                )
        except Exception as e:
            logger.error(f"[PULSE] Failed to initialize OllamaCivicAnalyzer: {e}")

    _default_analyzer = LocalCivicAnalyzer()
    logger.info("[PULSE] Using LocalCivicAnalyzer (offline heuristic engine).")
    return _default_analyzer

def analyze_and_store_feedback(feedback_item: FeedbackItem, analyzer: Optional[BaseCivicAnalyzer] = None) -> FeedbackAnalysis:
    """
    Executes multilingual analysis on a FeedbackItem, maps foreign keys to official RMC master data,
    and saves the FeedbackAnalysis record.
    """
    if analyzer is None:
        analyzer = get_analyzer()

    result = analyzer.analyze(feedback_item.raw_text, metadata=feedback_item.raw_metadata)

    # 1. Map Department — try exact code first, then fuzzy name match
    dept = None
    if result.department_code:
        dept = Department.objects.filter(code=result.department_code).first()
        if not dept:
            # Try partial name match (e.g. "drainage" matches "drainage-sewerage")
            slug = result.department_code.replace("-", " ")
            dept = Department.objects.filter(name__icontains=slug).first()
        if not dept:
            # Try matching any word in the code
            for word in result.department_code.split("-"):
                if len(word) > 3:
                    dept = Department.objects.filter(code__icontains=word).first()
                    if dept:
                        break

    # 2. Map Category — try exact code (with or without dept), then first category of dept
    category = None
    if result.category_code:
        # Exact match with dept
        if dept:
            category = CivicCategory.objects.filter(
                department=dept, code=result.category_code
            ).first()
        # Exact match across all depts
        if not category:
            category = CivicCategory.objects.filter(code=result.category_code).first()
            if category and not dept:
                dept = category.department  # infer dept from category
        # Fuzzy: match category name by any keyword in the code
        if not category and dept:
            for word in result.category_code.replace("-", " ").split():
                if len(word) > 3:
                    category = CivicCategory.objects.filter(
                        department=dept, code__icontains=word
                    ).first()
                    if not category:
                        category = CivicCategory.objects.filter(
                            code__icontains=word
                        ).first()
                    if category:
                        break
        # Last resort: first category of the matched dept
        if not category and dept:
            category = CivicCategory.objects.filter(department=dept).first()

    # 3. Map Location — official ward number is authoritative
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
