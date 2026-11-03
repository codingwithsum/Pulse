import os
from typing import Optional, Set

class Settings:
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "pulse_verify_token_2026")
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "rmc_civicpulse_secret_2026")
    WHATSAPP_ACCESS_TOKEN: Optional[str] = os.getenv("WHATSAPP_ACCESS_TOKEN", None)
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = os.getenv("WHATSAPP_PHONE_NUMBER_ID", None)

    # Allowed tokens set to prevent mismatches
    ALLOWED_VERIFY_TOKENS: Set[str] = {
        os.getenv("WHATSAPP_VERIFY_TOKEN", "pulse_verify_token_2026"),
        "pulse_verify_token_2026",
        "rmc_civicpulse_verify_token_2026",
        "rmc_secure_verify_token_2026",
    }

settings = Settings()
