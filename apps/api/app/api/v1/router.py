"""Main v1 API router - aggregates all module routers."""
from fastapi import APIRouter
from app.api.v1.routers import (
    auth,
    users,
    categories,
    agents,
    marketplace,
    execution,
    billing,
    admin,
    health,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(categories.router, prefix="/categories", tags=["categories"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(execution.router, prefix="/executions", tags=["execution"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
