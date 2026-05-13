import asyncio

import httpx
import pytest

from app.core.retry import retry_async
from app.core.settings import Settings, validate_startup_settings
from app.services.ocr_service import OcrResult
from app.services.storage_service import upload_image

from conftest import create_profile, register_user


OCR_TEXT = """
Nutrition Facts
Serving size 45g
Calories 220
Total Sugars 18g
Protein 6g
"""


async def fake_ocr_success(image_bytes: bytes, content_type: str) -> OcrResult:
    return OcrResult(text=OCR_TEXT, confidence=0.8, provider="test")


def test_rate_limit_for_analyse(client, auth_headers, image_file, monkeypatch):
    from app.core.settings import get_settings

    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    with open(image_file, "rb") as first:
        first_response = client.post(
            "/api/v1/analyse",
            headers=auth_headers,
            data={"question": "First request"},
            files={"image": ("label.png", first, "image/png")},
        )
    with open(image_file, "rb") as second:
        second_response = client.post(
            "/api/v1/analyse",
            headers=auth_headers,
            data={"question": "Second request"},
            files={"image": ("label.png", second, "image/png")},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429
    assert "rate limit" in second_response.json()["detail"].lower()


def test_redis_rate_limit_falls_back_to_memory_when_unavailable(client, auth_headers, image_file, monkeypatch):
    from app.core.settings import get_settings

    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    with open(image_file, "rb") as first:
        first_response = client.post(
            "/api/v1/analyse",
            headers=auth_headers,
            data={"question": "First request"},
            files={"image": ("label.png", first, "image/png")},
        )
    with open(image_file, "rb") as second:
        second_response = client.post(
            "/api/v1/analyse",
            headers=auth_headers,
            data={"question": "Second request"},
            files={"image": ("label.png", second, "image/png")},
        )

    assert first_response.status_code == 200
    assert second_response.status_code == 429


def test_retry_async_retries_transient_failure():
    attempts = {"count": 0}

    async def flaky_operation():
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise httpx.ConnectError("temporary failure")
        return "ok"

    result = asyncio.run(retry_async(flaky_operation, retries=2, initial_delay_seconds=0))

    assert result == "ok"
    assert attempts["count"] == 2


def test_storage_disabled_falls_back_to_in_memory(monkeypatch):
    from app.core.settings import get_settings

    monkeypatch.setenv("STORAGE_ENABLED", "false")
    get_settings.cache_clear()

    result = asyncio.run(
        upload_image(
            image_bytes=b"image",
            content_type="image/png",
            user_id="user-id",
        )
    )

    assert result is None


def test_request_size_limit_returns_413(client, auth_headers, monkeypatch):
    from app.core.settings import get_settings

    monkeypatch.setenv("MAX_REQUEST_BYTES", "10")
    get_settings.cache_clear()

    response = client.post(
        "/api/v1/analyse",
        headers={**auth_headers, "Content-Length": "11"},
        content=b"too large payload",
    )

    assert response.status_code == 413
    assert "too large" in response.json()["detail"].lower()


def test_startup_config_validation_requires_critical_env():
    settings = Settings(
        DATABASE_URL=None,
        SUPABASE_JWT_SECRET=None,
        STORAGE_ENABLED=False,
    )

    with pytest.raises(RuntimeError) as exc:
        validate_startup_settings(settings)

    message = str(exc.value)
    assert "DATABASE_URL" in message
    assert "SUPABASE_JWT_SECRET" in message


def test_production_config_rejects_wildcard_cors():
    settings = Settings(
        DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db",
        SUPABASE_JWT_SECRET="secret",
        PRODUCTION_MODE=True,
        CORS_ORIGINS=["*"],
    )

    with pytest.raises(RuntimeError) as exc:
        validate_startup_settings(settings)

    assert "CORS_ORIGINS" in str(exc.value)


def test_rag_embedding_empty_query_falls_back_to_no_random_chunks():
    from app.services.rag_service import _embed_query

    assert asyncio.run(_embed_query("   ")) is None
