import hashlib
import uuid
from typing import Optional, Dict, Any, Tuple
from django.utils import timezone
from apps.ingestion.models import DataSource
from apps.feedback.models import FeedbackItem
from apps.intelligence.models import FeedbackAnalysis
from apps.intelligence.services import analyze_and_store_feedback

def get_or_create_datasource_for_source(source_hint: str) -> DataSource:
    """Returns or creates the appropriate DataSource instance for the source."""
    s = (source_hint or "").lower().strip()
    if "twitter" in s or s in ("tw", "x"):
        ds, _ = DataSource.objects.get_or_create(
            source_type="TWITTER_X",
            defaults={"name": "Twitter / X (Official API v2)", "health_status": "HEALTHY"}
        )
        return ds
    elif "facebook" in s or s in ("fb", "meta"):
        ds, _ = DataSource.objects.get_or_create(
            source_type="FACEBOOK",
            defaults={"name": "Meta (Facebook & Instagram Feed)", "health_status": "HEALTHY"}
        )
        return ds
    elif "email" in s or "gmail" in s:
        ds, _ = DataSource.objects.get_or_create(
            source_type="EMAIL",
            defaults={"name": "Gmail / Authorized Municipal Inbox", "health_status": "HEALTHY"}
        )
        return ds
    elif "portal" in s or "website" in s or "rmc" in s:
        ds, _ = DataSource.objects.get_or_create(
            source_type="RMC_PORTAL",
            defaults={"name": "RMC Citizen Grievance Portal", "health_status": "HEALTHY"}
        )
        return ds
    elif "whatsapp" in s or s == "wa":
        ds, _ = DataSource.objects.get_or_create(
            source_type="WHATSAPP",
            defaults={"name": "WhatsApp Business Cloud API", "health_status": "HEALTHY"}
        )
        return ds
    else:
        ds, _ = DataSource.objects.get_or_create(
            source_type="RMC_PORTAL",
            defaults={"name": "RMC Official Portal / Direct", "health_status": "HEALTHY"}
        )
        return ds


def ingest_citizen_complaint(
    raw_text: str,
    source_hint: str,
    external_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    published_at: Optional[Any] = None,
    is_synthetic: bool = False
) -> Tuple[Optional[FeedbackItem], Optional[FeedbackAnalysis]]:
    """
    Ingests a civic complaint into PULSE with automatic source identification:
    - Twitter → Social Media → Twitter (X)
    - Facebook → Social Media → Facebook
    - Email → Via Email → Gmail
    - Portal → Official Website → RMC Portal

    Citizens never manually choose the source.
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None, None

    normalized_text = " ".join(raw_text.lower().split())
    content_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()

    existing = FeedbackItem.objects.filter(content_hash=content_hash).first()
    if existing:
        analysis = existing.analyses.filter(is_active_version=True).first()
        return existing, analysis

    data_source = get_or_create_datasource_for_source(source_hint)
    if not external_id:
        external_id = f"{source_hint.lower()[:3]}-{uuid.uuid4().hex[:8]}"

    if not published_at:
        published_at = timezone.now()

    meta = metadata or {}
    meta.setdefault("intake_source", source_hint)

    item = FeedbackItem(
        data_source=data_source,
        external_id=external_id,
        content_hash=content_hash,
        raw_text=raw_text,
        published_at=published_at,
        raw_metadata=meta,
        is_synthetic=is_synthetic,
        status="PENDING_ANALYSIS"
    )
    # Automatic detection runs in detect_source / save
    item.detect_source()
    item.save()

    analysis = analyze_and_store_feedback(item)
    return item, analysis

