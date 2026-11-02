# AgentHub — Engineering Baseline Audit Report

**Date**: 2026-11-02  
**Auditor**: Principal Software & Security Engineer  
**Status**: Completed Baseline Inspection  

---

## 1. Executive Summary

This audit assesses the current codebase of **AgentHub**, an AI Agent Marketplace and Agent Creation Platform. The repository consists of a FastAPI backend (`apps/api`), a Next.js 14 frontend (`apps/web`), shared documentation, and infrastructure definitions. 

While the system contains functional scaffolding, models, and 18 passing backend integration tests, several critical security, reliability, data integrity, and architectural issues must be remediated before production readiness.

---

## 2. Key Findings by Domain

### 2.1 Architecture & Entry Points
- **Backend Entry Point**: `apps/api/app/main.py` running on `uvicorn app.main:app`. Lifespan runs `Base.metadata.create_all` and `init_db()`.
- **Frontend Entry Point**: `apps/web/app/layout.tsx` and `app/page.tsx` running Next.js 14 on port 3000.
- **Workers**: `workers/` directories exist, but background execution currently relies on FastAPI in-process `BackgroundTasks`.

### 2.2 Security Vulnerabilities (Critical)
1. **Predictable Default Admin Credentials**: `apps/api/app/database/init_db.py` statically hardcoded `admin@agenthub.example` with password `Admin@AgentHub1`.
2. **Missing Administrative Bootstrap Tool**: No dedicated CLI command exists to create the initial super-admin with a strong, randomized, or operator-supplied credential.
3. **Weak Session Invalidation & No Refresh Token Rotation**:
   - `/auth/logout` merely clears the cookies client-side without revoking or invalidating the refresh token server-side.
   - Refresh tokens cannot be revoked if compromised; tokens are not tracked in a revocable store or database.
4. **Lack of CSRF Protection**: State-changing endpoints rely on `SameSite=lax` cookies alone, lacking CSRF tokens or header validation against cross-origin attacks.
5. **Payment Verification Flaws**:
   - `/api/v1/billing/verify` allowed client-supplied `amount_minor` and `agent_id`, enabling client-side price tampering.
   - Razorpay signature verification checked HMAC of `payment_id` alone instead of documented `f"{order_id}|{payment_id}"`.
   - Payment simulator allowed arbitrary IDs without binding to a prior server-generated checkout session.
6. **Marketplace Authorization & Integrity Bypasses**:
   - Reviews and bookmarks lacked mandatory `get_current_active_user` dependency, allowing anonymous placeholder IDs.
   - Lack of unique constraints on `(agent_id, user_id)` for reviews allowed review spamming.
   - Missing check for agent approval status prior to accepting reviews.

### 2.3 Execution Engine Reliability
1. **In-Process Task Execution**: Execution runs via `BackgroundTasks.add_task()`. Server restarts permanently drop queued or running tasks.
2. **In-Memory SSE Queues**: SSE updates rely entirely on an in-memory `_event_queues` dictionary. Reconnecting clients cannot replay missed events.
3. **No Cooperative Cancellation**: Cancelling an execution sets status to `CANCELLED` in the database, but does not abort the in-flight asynchronous LLM/tool task.
4. **Lack of Entitlement Enforcement**: `/api/v1/executions/` did not verify if the user purchased or held an active subscription for paid agents (`pricing_type != 'free'`).

### 2.4 Database & Migrations
1. **Missing Alembic Migration Versions**: `alembic.ini` exists, but `alembic/` migration environment has not been initialized with revisions.
2. **Missing Unique Constraints**:
   - `agent_reviews`: needs unique `(agent_id, user_id)`.
   - `agent_bookmarks`: needs unique `(agent_id, user_id)`.
   - `agent_versions`: needs unique `(agent_id, version_number)`.
   - `subscriptions`: needs index on `(user_id, status)`.

### 2.5 Integrations Status
| Integration | Status | Notes |
|---|---|---|
| **Google Gemini** | Functional | Requires `GEMINI_API_KEY`; fallback to dev adapter |
| **OpenAI** | Functional | Requires `OPENAI_API_KEY`; fallback to dev adapter |
| **Anthropic** | Functional | Requires `ANTHROPIC_API_KEY`; fallback to dev adapter |
| **Ollama** | Functional | Local endpoint HTTP client |
| **Development Adapter**| Functional | Deterministic, clearly labeled test fallback |
| **Payment Simulator** | Functional | Must be strictly disabled in production |
| **Razorpay / Stripe** | Implemented | Needs strict server-side checkout association |

---

## 3. Remediation Roadmap

The following phases will be executed in order:
- **Phase 2**: Critical Security Fixes (Auth, Marketplace, Agent Ownership, Payment & Billing).
- **Phase 3**: Execution Engine Reliability (Durable dispatch, event persistence, cooperative cancellation).
- **Phase 4**: Entitlements and Pricing Verification.
- **Phase 5**: Model Adapters & Deterministic Testing.
- **Phase 6**: Database Migrations & Integrity Constraints.
- **Phase 7**: Frontend Corrections & Reconnect SSE.
- **Phase 8**: Automated Testing (Target: comprehensive test coverage).
- **Phase 9**: CI/CD Workflows.
- **Phase 10**: Deployment Hardening & Production Checklist.
- **Phase 11**: Final Audit Report (`docs/audit/FINAL_AUDIT_REPORT.md`).
