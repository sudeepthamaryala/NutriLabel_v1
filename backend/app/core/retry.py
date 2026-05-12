import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

T = TypeVar("T")

TRANSIENT_HTTP_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def is_transient_http_error(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in TRANSIENT_HTTP_STATUS_CODES
    if isinstance(exc, httpx.ConnectError):
        return True
    return False


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    retries: int = 2,
    initial_delay_seconds: float = 0.2,
    is_retryable: Callable[[BaseException], bool] = is_transient_http_error,
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as exc:
            if attempt >= retries or not is_retryable(exc):
                raise
            await asyncio.sleep(initial_delay_seconds * (2**attempt))
            attempt += 1

