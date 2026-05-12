import logging

import httpx
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.core.database import get_engine
from app.core.settings import get_settings
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    try:
        engine = get_engine()
        async with engine.connect() as connection:
            await connection.execute(text("select 1"))
    except Exception:
        logger.exception("health_db_check_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        )
    await _check_external_services_if_enabled()
    return HealthResponse(status="ok")


async def _check_external_services_if_enabled() -> None:
    settings = get_settings()
    if not settings.health_check_external_services:
        return

    urls = [
        url
        for url in (settings.ocr_service_url, settings.inference_service_url, settings.embedding_service_url)
        if url
    ]
    if not urls:
        return

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            for url in urls:
                response = await client.get(url)
                if response.status_code >= 500:
                    raise httpx.HTTPStatusError("service unhealthy", request=response.request, response=response)
    except httpx.HTTPError:
        logger.exception("health_external_check_failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="External service is unavailable",
        )
