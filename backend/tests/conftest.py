import asyncio
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from fastapi.testclient import TestClient
from jose import jwt
from PIL import Image, ImageDraw


TEST_SECRET = "analyse-test-secret"


def _database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL is required for backend DB tests")
    return url


def _asyncpg_url() -> str:
    return _database_url().replace("postgresql+asyncpg://", "postgresql://", 1)


async def _reset_database() -> None:
    connection = await asyncpg.connect(_asyncpg_url())
    try:
        schema = Path("app/db/schema.sql").read_text(encoding="utf-8")
        await connection.execute(schema)
        await connection.execute(
            "truncate table chat_messages, chat_sessions, health_profiles, users restart identity cascade"
        )
    finally:
        await connection.close()


@pytest.fixture(autouse=True)
def test_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", _database_url())
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SUPABASE_JWT_AUDIENCE", "authenticated")
    monkeypatch.delenv("OCR_SERVICE_URL", raising=False)
    monkeypatch.delenv("INFERENCE_SERVICE_URL", raising=False)

    from app.core.database import get_engine, get_sessionmaker
    from app.core.settings import get_settings

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()
    asyncio.run(_reset_database())
    yield
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def user_token() -> tuple[str, str]:
    user_id = str(uuid4())
    token = jwt.encode(
        {
            "sub": user_id,
            "email": "analyse-test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    return user_id, token


@pytest.fixture
def auth_headers(user_token):
    _, token = user_token
    return {"Authorization": f"Bearer {token}", "X-Request-ID": "test-request-id"}


@pytest.fixture
def image_file(tmp_path):
    path = tmp_path / "label.png"
    image = Image.new("RGB", (600, 360), "white")
    draw = ImageDraw.Draw(image)
    draw.text((20, 20), "Nutrition Facts\nCalories 220\nTotal Sugars 18g\nProtein 6g", fill="black")
    image.save(path)
    return path


def register_user(client: TestClient, headers: dict) -> None:
    response = client.post("/api/v1/auth/register", headers=headers, json={"full_name": "Analyse User"})
    assert response.status_code == 201, response.text


def create_profile(client: TestClient, headers: dict) -> None:
    response = client.put(
        "/api/v1/profile",
        headers=headers,
        json={
            "age": 30,
            "weight_kg": "72.50",
            "height_cm": "175.00",
            "sex": "other",
            "activity_level": "moderate",
            "goal": "weight_maintenance",
            "allergies": ["peanuts"],
            "diseases": ["diabetes"],
            "dietary_preferences": ["vegetarian"],
        },
    )
    assert response.status_code == 200, response.text


async def fetch_chat_counts() -> tuple[int, int]:
    connection = await asyncpg.connect(_asyncpg_url())
    try:
        session_count = await connection.fetchval("select count(*) from chat_sessions")
        message_count = await connection.fetchval("select count(*) from chat_messages")
        return int(session_count), int(message_count)
    finally:
        await connection.close()


def fake_settings(**overrides):
    defaults = {
        "inference_service_url": None,
        "external_service_timeout_seconds": 0.01,
        "external_retry_attempts": 2,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)
