"""Small, dependency-free HTTP hardening middleware."""

import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from time import monotonic
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import JSONResponse, Response


logger = logging.getLogger("backend.http")


class RequestContextMiddleware:
    """Attach a correlation ID and log request completion details."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        request_id = request.headers.get("x-request-id") or str(uuid4())
        started = time.perf_counter()
        status_code = 500

        async def send_with_context(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers["x-request-id"] = request_id
            await send(message)

        await self.app(scope, receive, send_with_context)
        logger.info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            status_code,
            (time.perf_counter() - started) * 1000,
        )


class SecurityHeadersMiddleware:
    """Apply conservative browser security headers to every response."""

    def __init__(self, app: Callable):
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("x-content-type-options", "nosniff")
                headers.setdefault("x-frame-options", "DENY")
                headers.setdefault("referrer-policy", "no-referrer")
                headers.setdefault("permissions-policy", "camera=(), microphone=(), geolocation=()")
                headers.setdefault("content-security-policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; img-src 'self' data:")
            await send(message)

        await self.app(scope, receive, send_with_headers)


class FixedWindowRateLimiter:
    """Bounded in-memory request limiter for a single API process."""

    def __init__(self, app: Callable, max_requests: int = 60, window_seconds: int = 60):
        self.app = app
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[tuple[str, str], deque[float]] = defaultdict(deque)

    def _allowed(self, client: str, path: str, now: float | None = None) -> bool:
        current = monotonic() if now is None else now
        bucket = self._requests[(client, path)]
        cutoff = current - self.window_seconds
        while bucket and bucket[0] <= cutoff:
            bucket.popleft()
        if len(bucket) >= self.max_requests:
            return False
        bucket.append(current)
        return True

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or scope["path"] not in {"/auth/login", "/auth/register", "/agent/chat"}:
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        forwarded = headers.get("x-forwarded-for")
        client = forwarded.split(",", 1)[0].strip() if forwarded else (scope.get("client") or ("unknown", 0))[0]
        if self._allowed(str(client), scope["path"]):
            await self.app(scope, receive, send)
            return

        response = JSONResponse(
            {"detail": "Too many requests. Please try again shortly."},
            status_code=429,
            headers={"retry-after": str(self.window_seconds)},
        )
        await response(scope, receive, send)
