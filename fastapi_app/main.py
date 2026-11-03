from typing import Optional
from fastapi import FastAPI, Query
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from .webhook import router as whatsapp_router
from .config import settings

app = FastAPI(
    title="RMC CivicPulse AI Backend",
    description="AI-Enabled Civic Intelligence Backend for Rajkot Municipal Corporation",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount WhatsApp webhook router
app.include_router(whatsapp_router)

@app.get("/")
def root(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    # Fallback in case Meta callback URL is entered without the path:
    if hub_mode == "subscribe" and hub_verify_token in settings.ALLOWED_VERIFY_TOKENS and hub_challenge is not None:
        return PlainTextResponse(content=hub_challenge, status_code=200)

    return {
        "service": "RMC CivicPulse AI Backend",
        "status": "operational",
        "webhook_endpoint": "/api/whatsapp/webhook"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "meta_integration": "ready_for_verification"
    }
