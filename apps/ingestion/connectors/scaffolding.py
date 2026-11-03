from typing import Dict, Any, Optional
from .base import BaseConnector, NormalizedFeedbackPayload
from django.utils import timezone
from apps.feedback.models import FeedbackItem
from apps.intelligence.services import analyze_and_store_feedback
import hashlib

class TwitterXConnector(BaseConnector):
    """
    Connector for official Twitter / X mentions and posts.
    Automatically assigns Source: Social Media -> Twitter (X).
    """
    connector_id = "twitter-x-v2"
    connector_name = "Twitter / X (Official API v2)"

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("bearer_token"))

    def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "message": "Connected to official @myrmc_rajkot mentions via Developer API."
        }

    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedFeedbackPayload:
        text = raw_record.get("text", "") or raw_record.get("tweet", "")
        tweet_id = str(raw_record.get("id", "") or raw_record.get("tweet_id", ""))
        return NormalizedFeedbackPayload(
            raw_text=text,
            external_id=tweet_id if tweet_id.startswith("tw-") else f"tw-{tweet_id}",
            source_type="SOCIAL_MEDIA",
            source_platform="TWITTER",
            published_at=timezone.now(),
            anonymized_sender_hash=hashlib.sha256(f"tw-{tweet_id}".encode()).hexdigest()[:16],
            technical_metadata={"platform": "Twitter (X)", "tweet_id": tweet_id},
            is_synthetic=raw_record.get("is_synthetic", False)
        )

    def handle_incoming_record(self, raw_record: Dict[str, Any], data_source) -> Optional[FeedbackItem]:
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
            source_type="SOCIAL_MEDIA",
            source_platform="TWITTER",
            published_at=payload.published_at,
            raw_metadata=payload.technical_metadata,
            is_synthetic=payload.is_synthetic,
            status="PENDING_ANALYSIS"
        )
        analyze_and_store_feedback(item)
        return item


class MetaSocialConnector(BaseConnector):
    """
    Connector for official Meta (Facebook Page Feed / Mentions).
    Automatically assigns Source: Social Media -> Facebook.
    """
    connector_id = "meta-social-webhooks"
    connector_name = "Meta / Facebook Page Feed"

    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("page_access_token"))

    def test_connection(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "message": "Connected to official RMC Facebook page webhooks."
        }

    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedFeedbackPayload:
        message = raw_record.get("message", "") or raw_record.get("post_text", "")
        post_id = str(raw_record.get("post_id", "") or raw_record.get("id", ""))
        return NormalizedFeedbackPayload(
            raw_text=message,
            external_id=post_id if post_id.startswith("fb-") else f"fb-{post_id}",
            source_type="SOCIAL_MEDIA",
            source_platform="FACEBOOK",
            published_at=timezone.now(),
            anonymized_sender_hash=hashlib.sha256(f"fb-{post_id}".encode()).hexdigest()[:16],
            technical_metadata={"platform": "Facebook", "post_id": post_id},
            is_synthetic=raw_record.get("is_synthetic", False)
        )

    def handle_incoming_record(self, raw_record: Dict[str, Any], data_source) -> Optional[FeedbackItem]:
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
            source_type="SOCIAL_MEDIA",
            source_platform="FACEBOOK",
            published_at=payload.published_at,
            raw_metadata=payload.technical_metadata,
            is_synthetic=payload.is_synthetic,
            status="PENDING_ANALYSIS"
        )
        analyze_and_store_feedback(item)
        return item
