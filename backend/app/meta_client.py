"""Meta Graph API client with mock-mode fallback.

In mock mode (META_MOCK_MODE=true) all outbound Meta calls return deterministic
stubbed responses so the entire app is fully runnable without live credentials.

Also provides the HMAC-SHA256 webhook signature verification helper used by the
webhook ingestion endpoint.
"""
from __future__ import annotations

import hmac
import hashlib
import secrets
import time
from typing import Any

from loguru import logger

from .config import settings


def sign_payload(payload_bytes: bytes, app_secret: str | None = None) -> str:
    """Return the Meta-style 'sha256=...' signature header value for a payload."""
    key = (app_secret or settings.META_APP_SECRET).encode()
    digest = hmac.new(key, payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def verify_signature(payload_bytes: bytes, header_value: str | None) -> bool:
    """Constant-time verification of X-Hub-Signature-256 header."""
    if not header_value or not header_value.startswith("sha256="):
        return False
    expected = sign_payload(payload_bytes)
    # hmac.compare_digest is constant-time
    return hmac.compare_digest(expected, header_value)


class MetaClient:
    """Thin client around Meta Graph endpoints. Switches to mock mode automatically."""

    def __init__(self) -> None:
        self.mock = settings.META_MOCK_MODE

    async def exchange_code_for_business_token(self, code: str) -> dict[str, Any]:
        """Exchange an Embedded Signup auth code for a long-lived business token.

        Real implementation would POST to https://graph.facebook.com/{version}/oauth/access_token
        with client_id, client_secret, code. In mock mode we return a deterministic
        synthetic token + ids derived from the code.
        """
        if self.mock:
            suffix = secrets.token_hex(6)
            return {
                "access_token": f"MOCK_BIZ_TOKEN_{code[:8]}_{suffix}",
                "token_type": "bearer",
                "expires_in": 60 * 60 * 24 * 60,  # 60 days
                "waba_id": f"100000000{suffix[:6]}",
                "business_id": f"200000000{suffix[:6]}",
                "phone_number_id": f"300000000{suffix[:6]}",
                "display_phone_number": f"+1555{int(time.time()) % 10000000:07d}",
                "verified_name": "Demo Business",
                "quality_rating": "GREEN",
            }
        raise NotImplementedError("Live Meta exchange not enabled in this build.")

    async def subscribe_app_to_waba(self, waba_id: str, business_token: str) -> dict[str, Any]:
        if self.mock:
            logger.info(f"[mock] Subscribed app to WABA {waba_id}")
            return {"success": True}
        raise NotImplementedError("Live Meta subscribe not enabled in this build.")

    async def register_phone_number(
        self, phone_number_id: str, business_token: str, pin: str = "000000"
    ) -> dict[str, Any]:
        if self.mock:
            logger.info(f"[mock] Registered phone {phone_number_id}")
            return {"success": True}
        raise NotImplementedError("Live Meta register not enabled in this build.")

    async def send_template(
        self,
        phone_number_id: str,
        business_token: str,
        to_wa_id: str,
        template_name: str,
        language_code: str,
        components: list[dict] | None = None,
    ) -> dict[str, Any]:
        """Send a template message. Mock returns a synthetic wamid."""
        if self.mock:
            wamid = f"wamid.MOCK_{secrets.token_hex(10).upper()}"
            return {
                "messaging_product": "whatsapp",
                "contacts": [{"input": to_wa_id, "wa_id": to_wa_id}],
                "messages": [{"id": wamid, "message_status": "accepted"}],
            }
        raise NotImplementedError("Live Meta send not enabled in this build.")


meta_client = MetaClient()
