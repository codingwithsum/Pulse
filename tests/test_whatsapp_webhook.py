import hmac
import hashlib
import json
import pytest
from fastapi.testclient import TestClient

from fastapi_app.main import app
from fastapi_app.config import settings

client = TestClient(app)

def compute_signature(payload_bytes: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={sig}"

# --------------------------------------------------------------------------
# 1. GET Verification Handshake Tests
# --------------------------------------------------------------------------

def test_get_webhook_verification_success():
    """Valid challenge handshake should return challenge as plain text with 200 OK."""
    challenge_val = "CHALLENGE_TEST_XYZ_12345"
    response = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": challenge_val
        }
    )
    assert response.status_code == 200
    assert response.text == challenge_val
    assert "text/plain" in response.headers.get("content-type", "")

def test_get_webhook_verification_invalid_token():
    """Invalid token must return 403 Forbidden."""
    response = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_token_here",
            "hub.challenge": "12345"
        }
    )
    assert response.status_code == 403
    assert "Verification failed" in response.text

def test_get_webhook_verification_invalid_mode():
    """Mode other than 'subscribe' must return 403 Forbidden."""
    response = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": settings.WHATSAPP_VERIFY_TOKEN,
            "hub.challenge": "12345"
        }
    )
    assert response.status_code == 403

# --------------------------------------------------------------------------
# 2. POST Signature Security Tests
# --------------------------------------------------------------------------

def test_post_webhook_missing_signature():
    """Request without X-Hub-Signature-256 must be rejected with 401."""
    payload = {"entry": []}
    response = client.post("/api/whatsapp/webhook", json=payload)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"

def test_post_webhook_invalid_signature():
    """Request with incorrect HMAC signature must be rejected with 401."""
    payload = {"entry": []}
    raw_body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/api/whatsapp/webhook",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000"
        }
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid signature"

def test_post_webhook_malformed_json():
    """Malformed non-JSON body must return 400 Bad Request."""
    malformed_body = b"not-a-valid-json-string{["
    sig = compute_signature(malformed_body, settings.WHATSAPP_APP_SECRET)
    response = client.post(
        "/api/whatsapp/webhook",
        content=malformed_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig
        }
    )
    assert response.status_code == 400
    assert "Malformed JSON" in response.json()["detail"]

# --------------------------------------------------------------------------
# 3. Message Parsing & Zero-PII Tests
# --------------------------------------------------------------------------

def test_post_webhook_parse_incoming_message():
    """Valid Meta message payload should parse message, hash phone number, and return 200."""
    synthetic_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919999999999",
                                "phone_number_id": "TEST_PHONE_ID"
                            },
                            "contacts": [
                                {
                                    "profile": {"name": "Citizen User"},
                                    "wa_id": "919876543210"
                                }
                            ],
                            "messages": [
                                {
                                    "from": "919876543210",
                                    "id": "wamid.TEST_MSG_ID_001",
                                    "timestamp": "1729760000",
                                    "type": "text",
                                    "text": {
                                        "body": "કાલાવડ રોડ પ્રેમ મંદિર પાસે મોટો ખાડો છે, તાત્કાલિક રીપેર કરો."
                                    }
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    raw_body = json.dumps(synthetic_payload).encode("utf-8")
    sig = compute_signature(raw_body, settings.WHATSAPP_APP_SECRET)

    response = client.post(
        "/api/whatsapp/webhook",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["messages_processed"] == 1
    assert data["statuses_processed"] == 0

    parsed_msg = data["details"]["messages"][0]
    assert parsed_msg["message_id"] == "wamid.TEST_MSG_ID_001"
    assert "ખાડો" in parsed_msg["text"]
    # Verify phone number was hashed, never stored verbatim
    assert "9876543210" not in parsed_msg["sender_hash"]
    assert len(parsed_msg["sender_hash"]) == 16

# --------------------------------------------------------------------------
# 4. Delivery & Status Receipt Event Tests
# --------------------------------------------------------------------------

def test_post_webhook_parse_status_event():
    """Status/delivery events (e.g. read/delivered) must be parsed separately from citizen complaints."""
    synthetic_status_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "phone_number_id": "TEST_PHONE_ID"
                            },
                            "statuses": [
                                {
                                    "id": "wamid.TEST_STATUS_MSG_002",
                                    "status": "delivered",
                                    "timestamp": "1729760100",
                                    "recipient_id": "919876543210"
                                },
                                {
                                    "id": "wamid.TEST_STATUS_MSG_003",
                                    "status": "read",
                                    "timestamp": "1729760110",
                                    "recipient_id": "919876543210"
                                }
                            ]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }

    raw_body = json.dumps(synthetic_status_payload).encode("utf-8")
    sig = compute_signature(raw_body, settings.WHATSAPP_APP_SECRET)

    response = client.post(
        "/api/whatsapp/webhook",
        content=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": sig
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["messages_processed"] == 0
    assert data["statuses_processed"] == 2

    st1 = data["details"]["statuses"][0]
    assert st1["status_id"] == "wamid.TEST_STATUS_MSG_002"
    assert st1["status"] == "delivered"

# --------------------------------------------------------------------------
# 5. Deduplication Safeguard Tests
# --------------------------------------------------------------------------

def test_post_webhook_duplicate_message_ignored():
    """Re-sending a payload with the same message_id should be ignored as duplicate."""
    dup_payload = {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {
                                    "from": "919111111111",
                                    "id": "wamid.DUPLICATE_ID_100",
                                    "type": "text",
                                    "text": {"body": "First delivery of complaint"}
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }

    raw_body = json.dumps(dup_payload).encode("utf-8")
    sig = compute_signature(raw_body, settings.WHATSAPP_APP_SECRET)

    # First send -> processed
    res1 = client.post(
        "/api/whatsapp/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig}
    )
    assert res1.status_code == 200
    assert res1.json()["messages_processed"] == 1

    # Second send with same message ID -> duplicate ignored
    res2 = client.post(
        "/api/whatsapp/webhook",
        content=raw_body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig}
    )
    assert res2.status_code == 200
    assert res2.json()["messages_processed"] == 0
    assert res2.json()["duplicates_ignored"] == 1
