"""Onboarding flow: exchange Embedded Signup code for business token, persist."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from .crypto_utils import encrypt
from .db import get_db
from .meta_client import meta_client
from .models import EmbeddedSignupExchange, WabaPublic, PhoneNumberPublic
from .tenancy import Principal, require_tenant

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


@router.post("/exchange")
async def exchange(
    body: EmbeddedSignupExchange,
    p: Principal = Depends(require_tenant),
):
    """Server-side exchange of the auth code for a long-lived business token.

    In mock mode the meta_client returns a synthetic token + WABA + phone.
    The business token is encrypted at rest with Fernet before storage and is
    NEVER returned in the response.
    """
    db = get_db()
    res = await meta_client.exchange_code_for_business_token(body.code)

    waba_id = body.waba_id or res["waba_id"]
    phone_number_id = body.phone_number_id or res["phone_number_id"]
    business_token = res["access_token"]

    # Subscribe app to WABA + register phone (mocked)
    await meta_client.subscribe_app_to_waba(waba_id, business_token)
    await meta_client.register_phone_number(phone_number_id, business_token)

    now_iso = datetime.now(timezone.utc).isoformat()

    # Persist WABA (idempotent on waba_id)
    waba_internal_id = str(uuid.uuid4())
    await db.wabas.update_one(
        {"waba_id": waba_id},
        {
            "$setOnInsert": {
                "_id": waba_internal_id,
                "id": waba_internal_id,
                "tenant_id": p.tenant_id,
                "waba_id": waba_id,
                "business_id": res.get("business_id"),
                "name": res.get("verified_name") or "Business Account",
                "created_at": now_iso,
            }
        },
        upsert=True,
    )
    waba_doc = await db.wabas.find_one({"waba_id": waba_id})
    # Enforce isolation: a WABA already belonging to another tenant cannot be claimed
    if waba_doc["tenant_id"] != p.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="WABA already claimed by another tenant",
        )

    # Encrypted credentials
    await db.waba_credentials.update_one(
        {"waba_id": waba_id},
        {
            "$set": {
                "waba_id": waba_id,
                "encrypted_business_token": encrypt(business_token),
                "updated_at": now_iso,
            },
            "$setOnInsert": {"_id": f"cred_{waba_id}", "created_at": now_iso},
        },
        upsert=True,
    )

    # Persist phone
    phone_internal_id = str(uuid.uuid4())
    await db.phone_numbers.update_one(
        {"phone_number_id": phone_number_id},
        {
            "$setOnInsert": {
                "_id": phone_internal_id,
                "id": phone_internal_id,
                "tenant_id": p.tenant_id,
                "waba_id": waba_id,
                "phone_number_id": phone_number_id,
                "display_phone_number": res.get("display_phone_number"),
                "verified_name": res.get("verified_name"),
                "quality_rating": res.get("quality_rating"),
                "created_at": now_iso,
            }
        },
        upsert=True,
    )

    logger.info(f"Tenant {p.tenant_id} onboarded WABA {waba_id} phone {phone_number_id}")

    waba_out = await db.wabas.find_one({"waba_id": waba_id})
    phone_out = await db.phone_numbers.find_one({"phone_number_id": phone_number_id})
    return {
        "waba": _serialize_waba(waba_out),
        "phone_number": _serialize_phone(phone_out),
    }


def _serialize_waba(doc: dict) -> dict:
    return WabaPublic(**doc).model_dump(mode="json")


def _serialize_phone(doc: dict) -> dict:
    return PhoneNumberPublic(**doc).model_dump(mode="json")
