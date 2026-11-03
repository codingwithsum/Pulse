from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class WhatsAppTextMessage(BaseModel):
    message_id: str
    sender_hash: str
    text: str
    timestamp: Optional[str] = None
    raw_type: str = "text"

class WhatsAppStatusEvent(BaseModel):
    status_id: str
    status: str  # sent, delivered, read, failed
    timestamp: Optional[str] = None
    recipient_hash: Optional[str] = None
    error: Optional[Dict[str, Any]] = None

class WebhookProcessingResult(BaseModel):
    status: str = "success"
    messages_processed: int = 0
    statuses_processed: int = 0
    duplicates_ignored: int = 0
    details: Dict[str, Any] = Field(default_factory=dict)
