"""Seed routine: creates platform super-admin + demo tenant owner on startup if missing."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from loguru import logger

from .auth import hash_password
from .db import get_db
from .models import Role


SUPER_ADMIN_EMAIL = "super@admin.com"
SUPER_ADMIN_PASSWORD = "SuperAdmin123!"
DEMO_OWNER_EMAIL = "owner@demo.com"
DEMO_OWNER_PASSWORD = "Owner123!"
DEMO_TENANT_NAME = "Demo Inc"


async def seed_initial_data() -> None:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()

    # Super admin (no tenant, MFA required)
    if not await db.users.find_one({"email": SUPER_ADMIN_EMAIL}):
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "_id": uid,
                "id": uid,
                "email": SUPER_ADMIN_EMAIL,
                "password_hash": hash_password(SUPER_ADMIN_PASSWORD),
                "full_name": "Platform Super Admin",
                "role": Role.PlatformSuperAdmin.value,
                "tenant_id": None,
                "mfa_enabled": False,
                "mfa_required": True,
                "mfa_secret_encrypted": None,
                "created_at": now,
            }
        )
        logger.info(f"Seeded super admin: {SUPER_ADMIN_EMAIL}")

    # Demo tenant + owner
    if not await db.users.find_one({"email": DEMO_OWNER_EMAIL}):
        tid = str(uuid.uuid4())
        await db.tenants.insert_one(
            {"_id": tid, "id": tid, "name": DEMO_TENANT_NAME, "created_at": now}
        )
        uid = str(uuid.uuid4())
        await db.users.insert_one(
            {
                "_id": uid,
                "id": uid,
                "email": DEMO_OWNER_EMAIL,
                "password_hash": hash_password(DEMO_OWNER_PASSWORD),
                "full_name": "Demo Owner",
                "role": Role.TenantOwner.value,
                "tenant_id": tid,
                "mfa_enabled": False,
                "mfa_required": False,
                "mfa_secret_encrypted": None,
                "created_at": now,
            }
        )
        logger.info(f"Seeded demo tenant ({DEMO_TENANT_NAME}) + owner: {DEMO_OWNER_EMAIL}")
