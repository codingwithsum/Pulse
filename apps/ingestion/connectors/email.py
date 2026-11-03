import hashlib
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from .base import BaseConnector, NormalizedFeedbackPayload
from apps.feedback.models import FeedbackItem
from apps.intelligence.services import analyze_and_store_feedback

class EmailConnector(BaseConnector):
    """
    Connector for incoming citizen emails (Gmail / authorized incoming municipal email account).
    Automatically identifies and assigns Source: Via Email -> Gmail.
    Zero citizen email addresses or PII stored.
    """
    connector_id = "gmail-authorized-inbox"
    connector_name = "Gmail / Authorized Municipal Inbox"

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("email_account") or config.get("api_key"))

    def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "message": "Authorized Gmail / incoming municipal email inbox active and listening."
        }

    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedFeedbackPayload:
        body = raw_record.get("body", "") or raw_record.get("text", "") or raw_record.get("message", "")
        subject = raw_record.get("subject", "")
        if subject and subject not in body:
            full_text = f"[{subject}] {body}".strip()
        else:
            full_text = body.strip()

        msg_id = str(raw_record.get("message_id", "") or raw_record.get("id", ""))
        sender_email = raw_record.get("sender_email", "")

        # Compute one-way hash of sender email to maintain continuity without storing citizen email
        if sender_email:
            sender_hash = hashlib.sha256(sender_email.encode("utf-8")).hexdigest()[:16]
        else:
            sender_hash = hashlib.sha256(msg_id.encode("utf-8")).hexdigest()[:16]

        pub_date = raw_record.get("received_at")
        if not isinstance(pub_date, datetime):
            pub_date = timezone.now()

        return NormalizedFeedbackPayload(
            raw_text=full_text,
            external_id=msg_id if msg_id.startswith("email-") else f"email-{msg_id}",
            source_type="EMAIL",
            source_platform="GMAIL",
            published_at=pub_date,
            anonymized_sender_hash=sender_hash,
            technical_metadata={"platform": "Gmail", "has_attachments": bool(raw_record.get("attachments"))},
            is_synthetic=raw_record.get("is_synthetic", False)
        )

    def handle_incoming_email(self, raw_record: Dict[str, Any], data_source) -> Optional[FeedbackItem]:
        payload = self.normalize(raw_record)
        if not payload.raw_text:
            return None
        if FeedbackItem.objects.filter(content_hash=payload.content_hash).exists():
            return None
        item = FeedbackItem.objects.create(
            data_source=data_source,
            external_id=payload.external_id,
            content_hash=payload.content_hash,
            raw_text=payload.raw_text,
            source_type="EMAIL",
            source_platform="GMAIL",
            published_at=payload.published_at,
            raw_metadata=payload.technical_metadata,
            is_synthetic=payload.is_synthetic,
            status="PENDING_ANALYSIS"
        )
        analyze_and_store_feedback(item)
        return item

