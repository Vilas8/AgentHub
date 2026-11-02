# Architecture Decision Records

## ADR-001: Modular Monolith API

**Status**: Accepted  
**Decision**: Start with a modular monolith FastAPI application with clearly defined module boundaries.  
**Rationale**: Faster initial development, easier debugging, simpler deployment. Module boundaries allow future extraction to microservices.

## ADR-002: SQLite for Local Dev, PostgreSQL for Production

**Status**: Accepted  
**Decision**: Use aiosqlite driver for local development when PostgreSQL is unavailable, asyncpg for production.  
**Rationale**: Reduces local setup friction. SQLAlchemy abstracts the difference.

## ADR-003: JWT in HttpOnly Cookies

**Status**: Accepted  
**Decision**: Store JWT access and refresh tokens in httpOnly, SameSite=Lax cookies.  
**Rationale**: Prevents XSS token theft. Refresh token rotation handled server-side.

## ADR-004: Provider-Independent Model Adapter

**Status**: Accepted  
**Decision**: All AI model calls go through a `ModelAdapter` interface. Concrete adapters for Gemini, OpenAI, Anthropic, Ollama.  
**Rationale**: Swap providers without changing business logic. Support fallback and routing.

## ADR-005: Integer Minor Currency Units

**Status**: Accepted  
**Decision**: All monetary values stored as integers in minor currency units (e.g. cents/paise).  
**Rationale**: Eliminates floating-point rounding errors in financial calculations.

## ADR-006: Immutable Financial Ledger

**Status**: Accepted  
**Decision**: Financial records are never updated or deleted. Corrections via compensating transactions.  
**Rationale**: Audit trail, regulatory compliance, debugging.

## ADR-007: Server-Sent Events for Execution Streaming

**Status**: Accepted  
**Decision**: Use SSE for streaming execution status to the browser.  
**Rationale**: SSE is simpler than WebSockets for unidirectional server→client streams, works through proxies.

## ADR-008: Declarative Agent Configurations Only (MVP)

**Status**: Accepted  
**Decision**: Agents are configured declaratively (JSON/YAML). No arbitrary code execution in MVP.  
**Rationale**: Security — eliminates arbitrary code execution risk. Custom code sandbox planned for v2.

## ADR-009: Payment Provider Adapters

**Status**: Accepted  
**Decision**: Payment operations go through a `PaymentProvider` interface. Dev simulator + Razorpay + Stripe adapters.  
**Rationale**: Multi-market support. Dev adapter clearly isolated from production.

## ADR-010: UUID Primary Keys

**Status**: Accepted  
**Decision**: All tables use UUID v4 primary keys.  
**Rationale**: Globally unique, safe to expose in APIs, no enumeration attacks.
