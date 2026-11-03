import hmac
import hashlib
import json
import logging
from collections import deque
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Request, Query, HTTPException, Response, status
from fastapi.responses import PlainTextResponse

from .config import settings
from .schemas import WhatsAppTextMessage, WhatsAppStatusEvent, WebhookProcessingResult

logger = logging.getLogger("civicpulse.whatsapp")
router = APIRouter()

# In-memory bounded cache for deduplicating message IDs
SEEN_MESSAGE_IDS = set()
MAX_SEEN_CACHE = 10000
SEEN_QUEUE = deque()

def hash_phone_number(raw_phone: str) -> str:
    """
    Data Minimization Rule: Converts citizen phone number to a salted SHA-256 hash.
    Never stores plain-text contact numbers.
    """
    if not raw_phone:
        return "anonymous_citizen"
    salt = "rmc_civicpulse_salt_2026"
    return hashlib.sha256(f"{salt}_{raw_phone}".encode("utf-8")).hexdigest()[:16]

def verify_meta_signature(raw_body: bytes, signature_header: Optional[str], secret: str) -> bool:
    """
    Validates Meta's X-Hub-Signature-256 header using HMAC-SHA256.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected_hash = signature_header[len("sha256="):]
    computed_hash = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected_hash, computed_hash)

def record_seen_id(msg_id: str) -> bool:
    """
    Checks if message ID was already processed. Returns True if new, False if duplicate.
    """
    if msg_id in SEEN_MESSAGE_IDS:
        return False
    if len(SEEN_QUEUE) >= MAX_SEEN_CACHE:
        old_id = SEEN_QUEUE.popleft()
        SEEN_MESSAGE_IDS.discard(old_id)
    SEEN_MESSAGE_IDS.add(msg_id)
    SEEN_QUEUE.append(msg_id)
    return True

@router.get("/api/whatsapp/webhook")
@router.get("/api/whatsapp/webhook/")
@router.get("/api/v1/integrations/whatsapp/webhook/")
async def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """
    Meta Webhook Verification Handshake:
    Validates hub.mode, hub.verify_token, and hub.challenge.
    Returns the challenge as plain text only when the token matches.
    """
    if (
        hub_mode == "subscribe"
        and hub_verify_token in settings.ALLOWED_VERIFY_TOKENS
        and hub_challenge is not None
    ):
        logger.info(f"WhatsApp webhook GET verification succeeded for token: {hub_verify_token}")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning(f"WhatsApp webhook GET verification failed: token={hub_verify_token}, mode={hub_mode}")
    return PlainTextResponse(content="Verification failed", status_code=403)

@router.post("/api/whatsapp/webhook", response_model=WebhookProcessingResult)
@router.post("/api/whatsapp/webhook/", response_model=WebhookProcessingResult)
@router.post("/api/v1/integrations/whatsapp/webhook/", response_model=WebhookProcessingResult)
async def receive_webhook(request: Request):
    """
    Meta Webhook Ingestion Endpoint:
    1. Validates HMAC-SHA256 signature against WHATSAPP_APP_SECRET.
    2. Parses incoming citizen messages separately from delivery/status receipts.
    3. Handles deduplication by message ID.
    4. Enforces data minimization (phone numbers hashed with SHA-256).
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    # Step 1: Validate HMAC-SHA256 signature
    if not verify_meta_signature(raw_body, signature, settings.WHATSAPP_APP_SECRET):
        logger.error("WhatsApp webhook signature validation failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid signature"
        )

    # Step 2: Parse raw JSON payload
    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as e:
        logger.error(f"Malformed JSON payload in webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed JSON payload"
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload structure: expected JSON object"
        )

    processed_messages: List[WhatsAppTextMessage] = []
    processed_statuses: List[WhatsAppStatusEvent] = []
    duplicates_count = 0

    entries = payload.get("entry", [])
    if not isinstance(entries, list):
        return WebhookProcessingResult(status="ignored", details={"reason": "no entries"})

    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})

            # -------------------------------------------------------------
            # Part A: Parse Delivery / Status Events (sent, delivered, read, failed)
            # -------------------------------------------------------------
            statuses = value.get("statuses", [])
            for st in statuses:
                status_id = st.get("id", "")
                status_val = st.get("status", "")
                recip = str(st.get("recipient_id", ""))
                err = st.get("errors")

                processed_statuses.append(WhatsAppStatusEvent(
                    status_id=status_id,
                    status=status_val,
                    timestamp=str(st.get("timestamp", "")),
                    recipient_hash=hash_phone_number(recip),
                    error=err[0] if isinstance(err, list) and err else None
                ))
                logger.info(f"WhatsApp Status Receipt: ID={status_id}, Status={status_val}")

            # -------------------------------------------------------------
            # Part B: Parse Incoming Citizen Messages
            # -------------------------------------------------------------
            messages = value.get("messages", [])
            for msg in messages:
                msg_id = msg.get("id", "")
                if not msg_id:
                    continue

                # Deduplication check
                if not record_seen_id(msg_id):
                    logger.info(f"Duplicate WhatsApp message ID {msg_id} ignored.")
                    duplicates_count += 1
                    continue

                raw_sender = str(msg.get("from", ""))
                sender_hash = hash_phone_number(raw_sender)

                msg_type = msg.get("type", "text")
                body_text = ""

                if msg_type == "text":
                    body_text = msg.get("text", {}).get("body", "")
                elif msg_type == "interactive":
                    btn = msg.get("interactive", {}).get("button_reply", {})
                    body_text = btn.get("title", "") or btn.get("id", "")
                elif msg_type in ["image", "document", "audio", "video", "location"]:
                    caption = msg.get(msg_type, {}).get("caption", "")
                    body_text = f"[{msg_type.upper()}] {caption}".strip()
                else:
                    body_text = f"[{msg_type.upper()} message]"

                processed_messages.append(WhatsAppTextMessage(
                    message_id=msg_id,
                    sender_hash=sender_hash,
                    text=body_text,
                    timestamp=str(msg.get("timestamp", "")),
                    raw_type=msg_type
                ))
                logger.info(f"Parsed citizen message: ID={msg_id}, SenderHash={sender_hash}")

    # Step 3: Persist to database and trigger civic intelligence analysis
    try:
        import os
        import django
        if not os.environ.get("DJANGO_SETTINGS_MODULE"):
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pulse_project.settings")
            django.setup()
        from apps.ingestion.connectors.whatsapp import WhatsAppCloudApiConnector
        from apps.ingestion.models import DataSource

        connector = WhatsAppCloudApiConnector()
        data_source = DataSource.objects.filter(source_type="WHATSAPP").first()
        if not data_source:
            data_source = DataSource.objects.create(
                name="WhatsApp Business Cloud API",
                source_type="WHATSAPP",
                health_status="HEALTHY"
            )
        connector.handle_incoming_webhook(payload, data_source)
        logger.info("Successfully persisted WhatsApp messages to database and generated AI analytics.")
    except Exception as e:
        logger.warning(f"Could not persist to Django database: {e}")

    return WebhookProcessingResult(
        status="success",
        messages_processed=len(processed_messages),
        statuses_processed=len(processed_statuses),
        duplicates_ignored=duplicates_count,
        details={
            "messages": [m.model_dump() for m in processed_messages],
            "statuses": [s.model_dump() for s in processed_statuses]
        }
    )
