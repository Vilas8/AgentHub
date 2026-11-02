"""Simple in-memory rate limiter middleware."""
import time
from collections import defaultdict
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_request_counts: dict[str, list[float]] = defaultdict(list)
WINDOW_SECONDS = 60
MAX_REQUESTS = 200  # per IP per minute (generous for dev)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window_start = now - WINDOW_SECONDS

        # Clean old entries
        _request_counts[client_ip] = [
            t for t in _request_counts[client_ip] if t > window_start
        ]

        if len(_request_counts[client_ip]) >= MAX_REQUESTS:
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests", "detail": "Rate limit exceeded. Try again later."},
            )

        _request_counts[client_ip].append(now)
        return await call_next(request)
