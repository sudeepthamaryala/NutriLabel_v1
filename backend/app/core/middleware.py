import logging
import time
from collections import defaultdict, deque
from contextlib import suppress
from uuid import uuid4

from fastapi import Request
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.settings import get_settings

logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id[:120]
        request.state.user_id = _extract_unverified_user_id(request)
        start = time.perf_counter()

        try:
            response = await call_next(request)
        finally:
            latency_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request.state.request_id,
                    "user_id": request.state.user_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "latency_ms": latency_ms,
                },
            )

        response.headers["X-Request-ID"] = request.state.request_id
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app) -> None:
        super().__init__(app)
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        if request.url.path not in {f"{settings.api_v1_prefix}/analyse", f"{settings.api_v1_prefix}/compare"}:
            return await call_next(request)

        key = _rate_limit_key(request)
        redis_client = getattr(request.app.state, "redis", None)
        if settings.redis_url and redis_client:
            limited = await _is_limited_by_redis(
                client=redis_client,
                key=key,
                limit=settings.rate_limit_requests,
                window_seconds=settings.rate_limit_window_seconds,
            )
            if limited is not None:
                if limited:
                    return _rate_limited_response(settings.rate_limit_window_seconds)
                return await call_next(request)

        now = time.monotonic()
        window_start = now - settings.rate_limit_window_seconds
        hits = self._requests[key]
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= settings.rate_limit_requests:
            return _rate_limited_response(settings.rate_limit_window_seconds)

        hits.append(now)
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
            if size > settings.max_request_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request payload is too large."},
                )
        return await call_next(request)


def _rate_limit_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None) or _extract_unverified_user_id(request)
    if user_id:
        return f"user:{user_id}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _extract_unverified_user_id(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header.split(" ", 1)[1].strip()
    try:
        claims = jwt.get_unverified_claims(token)
    except JWTError:
        return None
    subject = claims.get("sub")
    return str(subject) if subject else None


async def _is_limited_by_redis(
    *,
    client,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool | None:
    with suppress(Exception):
        redis_key = f"rate-limit:{key}"
        count = await client.incr(redis_key)
        if count == 1:
            await client.expire(redis_key, window_seconds)
        return count > limit
    return None


def _rate_limited_response(window_seconds: int) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Please try again shortly."},
        headers={"Retry-After": str(window_seconds)},
    )
