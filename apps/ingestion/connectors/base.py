import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

@dataclass
class NormalizedFeedbackPayload:
    """
    Standardized in-flight payload produced by all connectors before database persistence.
    Guarantees strict data minimization and provenance tracking.
    """
    raw_text: str
    external_id: str
    source_type: str
    published_at: datetime
    anonymized_sender_hash: str
    source_platform: Optional[str] = None
    technical_metadata: Dict[str, Any] = field(default_factory=dict)
    is_synthetic: bool = False

    @property
    def content_hash(self) -> str:
        """Computes deterministic SHA-256 hash of normalized text for deduplication."""
        normalized = " ".join(self.raw_text.strip().lower().split())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


@dataclass
class IngestionBatchResult:
    total_processed: int = 0
    new_items_count: int = 0
    duplicates_blocked: int = 0
    errors_count: int = 0
    error_details: List[str] = field(default_factory=list)


class BaseConnector(ABC):
    """
    Universal connector interface for all intake channels.
    Future integrations (WhatsApp, email, Twitter, RMC portal) implement this contract.
    """
    connector_id: str
    connector_name: str

    @abstractmethod
    def validate_configuration(self, config: Dict[str, Any]) -> bool:
        """Validates that necessary tokens, endpoints, and secrets are present."""
        pass

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Tests connectivity and reports health status."""
        pass

    @abstractmethod
    def normalize(self, raw_record: Dict[str, Any]) -> NormalizedFeedbackPayload:
        """Normalizes source-specific record into standard NormalizedFeedbackPayload."""
        pass
