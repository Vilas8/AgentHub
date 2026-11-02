# AgentHub REST API Reference

All endpoints are versioned under `/api/v1/`.

## Authentication & Session
- `POST /api/v1/auth/register` — Register a new customer or creator account.
- `POST /api/v1/auth/login` — Authenticate and receive httpOnly JWT session cookies.
- `POST /api/v1/auth/logout` — Invalidate session cookies.
- `GET /api/v1/auth/me` — Inspect current authenticated user identity and role.

## Marketplace (Public Discovery)
- `GET /api/v1/marketplace/agents` — Paginated search, category filtering, and sorting (`newest`, `popular`, `rating`).
- `GET /api/v1/marketplace/agents/{id}` — Fetch detailed agent profile and capabilities.
- `GET /api/v1/categories/` — List all active agent categories.

## Agent Registry & Creator Studio
- `GET /api/v1/agents/my` — List all agents owned by the authenticated creator.
- `POST /api/v1/agents/` — Create a new agent definition.
- `PATCH /api/v1/agents/{id}` — Update agent metadata.
- `POST /api/v1/agents/{id}/versions` — Create an immutable version snapshot with system prompt & model config.
- `POST /api/v1/agents/{id}/submit-review` — Submit agent to moderation queue.

## Execution Engine
- `POST /api/v1/executions/` — Enqueue an agent execution job with task payload.
- `GET /api/v1/executions/{id}` — Query execution status, duration, token usage, and output data.
- `GET /api/v1/executions/{id}/stream` — Server-Sent Events (SSE) live execution step stream.
- `POST /api/v1/executions/{id}/cancel` — Cancel an in-progress execution.

## Billing & Creator Economy
- `GET /api/v1/billing/creator/balance` — View creator available, pending, and total lifetime earnings.
- `GET /api/v1/billing/creator/ledger` — Inspect immutable audit ledger of all revenue credits and payouts.

## Administration
- `GET /api/v1/admin/overview` — Platform telemetry (users, agents, pending reviews, executions).
- `GET /api/v1/admin/agents/pending` — Moderation review queue.
- `POST /api/v1/admin/agents/{id}/approve` — Approve and publish agent to marketplace.
- `POST /api/v1/admin/agents/{id}/reject` — Reject agent submission with audit log.
