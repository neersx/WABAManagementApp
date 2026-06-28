# plan.md

## 1) Objectives
- Deliver Phase 1 MVP of a **multi-tenant WhatsApp SaaS (mock Meta mode)** on Emergent FARM stack.
- Prove the **core workflow** works end-to-end: connect WhatsApp (mock) → send template (idempotent) → webhook verify+enqueue (<1s) → worker projection → message status updates.
- Enforce **tenant isolation**, **RBAC**, **MFA (TOTP)**, audit log, health/metrics.

## 2) Implementation Steps

### Phase 1 — Core Flow POC (Isolation) (do not proceed until green)
**Goal:** Validate the failure-prone pipeline (signature verify + fast ACK + queue + worker projection + idempotency) without full UI/auth.
1. Backend-only POC endpoints (no auth):
   - `POST /api/poc/onboarding/exchange` (mock) → creates tenant + waba + phone
   - `POST /api/poc/messages/send` (mock) → creates message with `queued` + idempotency key
   - `POST /api/webhooks/meta` → verifies `X-Hub-Signature-256`, stores raw event, enqueues job, returns in <1s
   - Worker loop claims `mq_jobs` and projects event → message status updates
2. Write a small Python script to:
   - create tenant/waba/phone, send template twice with same idempotency key
   - post a simulated webhook with valid signature then invalid signature
   - assert: single message created, 401/403 on bad signature, statuses advance queued→sent→delivered/read
3. Add Mongo indexes/TTL + atomic claim (`find_one_and_update`) + idempotency unique constraint.

**User stories (Phase 1)**
1. As a developer, I can create a mock WABA+phone via an API call so I can test messaging quickly.
2. As a developer, I can send a template message and see it recorded as `queued`.
3. As a developer, sending the same request with the same idempotency key only creates one message.
4. As a system, the webhook endpoint rejects invalid signatures.
5. As a system, a valid webhook is ACKed quickly and processed asynchronously by the worker.

---

### Phase 2 — V1 App Development (MVP UI + full API)
**Backend (FastAPI modular monolith)**
1. Create modules: `db.py`, `models.py`, `tenancy.py`, `auth.py`, `crypto_utils.py`, `meta_client.py` (mock), `onboarding.py`, `messaging.py`, `webhooks.py`, `worker.py`, `admin_routes.py`, `health.py`, `server.py`.
2. Auth:
   - Email+password, bcrypt hashing
   - JWT access (~15m) + rotating refresh tokens in httpOnly cookies
   - Password reset flow (log reset link to console)
   - TOTP MFA (required for super-admin, optional for others)
   - RBAC guards (PlatformSuperAdmin, TenantOwner, TenantAdmin, Agent, Viewer)
3. Multi-tenancy:
   - `tenant_id` embedded in JWT; dependency injects current tenant
   - repository helpers enforce `{tenant_id: ...}` on every tenant-owned collection
4. Onboarding:
   - `POST /api/onboarding/exchange` (mock embedded signup exchange) persists WABA + phone + encrypted token
   - `GET /api/wabas`, `GET /api/phone-numbers`
5. Messaging:
   - `POST /api/messages/send` with idempotency + per-phone rate limit
   - `GET /api/messages` paginated log
   - Admin helper: `POST /api/messages/{id}/simulate-webhook` to generate delivery/read events
6. Webhooks/worker:
   - `GET /api/webhooks/meta` verify challenge
   - `POST /api/webhooks/meta` verify signature, raw store, enqueue, fast ACK
   - Worker projects events into `messages`/`conversations`
7. Observability + ops:
   - structured logs w/ request trace id
   - `/health/live`, `/health/ready`, `/metrics`
   - audit log for key actions
8. Seed data on startup:
   - `super@admin.com / SuperAdmin123!`
   - `owner@demo.com / Owner123!`

**Frontend (React SPA)**
1. Public marketing routes: `/`, `/pricing`, `/features`, `/contact` with responsive layout + meta tags.
2. Auth routes: `/login`, `/register`, `/forgot-password`, `/reset-password`, `/mfa/verify`.
3. Protected admin routes: `/app/dashboard`, `/app/connect`, `/app/wabas`, `/app/send`, `/app/messages`, `/app/security`.
4. Core UI flows:
   - Register → creates tenant+owner → dashboard
   - Connect WhatsApp → launch mock embedded signup → exchange → WABA/phone appears
   - Send template → queued→sent; simulate webhook → delivered/read
   - Message log with pagination and status badges
5. API client:
   - axios w/ credentials + refresh retry on 401
   - AuthContext + ProtectedRoute

**End of Phase 2:** run `testing_agent_v3` for a full V1 pass; fix all high/medium issues.

**User stories (Phase 2)**
1. As a visitor, I can browse marketing pages and click Get Started.
2. As a new user, I can register and immediately land on my tenant dashboard.
3. As a returning user, I can log in and complete MFA if enabled.
4. As a tenant owner, I can connect WhatsApp via a mock embedded signup and see WABAs/phones listed.
5. As a tenant owner, I can send a template message and see it appear in the message log.

---

### Phase 3 — Hardening + Coverage (tests + security + tenant isolation proof)
1. Add backend tests (pytest):
   - tenant isolation (cannot access other tenant data)
   - webhook signature (good/bad)
   - idempotency
   - refresh token rotation + revoke
2. Add UI-level sanity tests (lightweight) + empty/error/loading states.
3. Tighten security:
   - ensure tokens never logged/returned
   - consistent 403 vs 404 for cross-tenant access
   - rate-limit enforcement tests
4. Run `testing_agent_v3` again and iterate until clean.

**User stories (Phase 3)**
1. As a tenant owner, I can’t access other tenants’ WABAs or messages even if I guess IDs.
2. As an admin, I can verify health/metrics endpoints respond.
3. As a user, I see clear errors when actions fail (invalid MFA code, invalid reset token, etc.).
4. As a tenant owner, sending duplicate requests doesn’t duplicate messages.
5. As an operator, I can see webhook processing succeed/fail in logs and raw event storage.

---

### Phase 4 — Polish + Delivery
1. UI polish: navigation, forms, toasts, loading skeletons, empty states.
2. Documentation: env vars, seed accounts, demo script (connect → send → simulate webhook).
3. Final `testing_agent_v3` run; fix remaining issues; deliver summary.

**User stories (Phase 4)**
1. As a demo user, I can complete the full flow in under 2 minutes without confusion.
2. As a user, I can enroll/disable MFA from Security settings.
3. As a super-admin, I’m forced to enroll MFA on first login.
4. As a tenant owner, I can filter/search message log and paginate reliably.
5. As an operator, I can confirm readiness/liveness/metrics endpoints for deployment.

## 3) Next Actions
1. Implement Phase 1 POC endpoints + Mongo queue + worker loop + signature helper.
2. Add the POC verification script and run it until all assertions pass.
3. Begin Phase 2 build (backend modules + React routes) in minimal large commits.

## 4) Success Criteria
- Core pipeline proven: **idempotent send**, **signature-verified webhook**, **<1s ACK**, **async worker projection**, **status updates**.
- V1 UI covers US1–US16 (mock-mode) with good error/empty/loading states.
- Tenant isolation verified by tests.
- Health/metrics endpoints respond.
- Seed accounts work and super-admin MFA is enforced.
