import asyncio

import pytest

from app.services.ocr_service import OcrResult, OcrServiceError

from conftest import create_profile, fake_settings, fetch_chat_counts, register_user


OCR_TEXT = """
Nutrition Facts
Serving size 45g
Calories 220
Total Fat 9g
Sodium 320mg
Total Sugars 18g
Protein 6g
Ingredients: oats, sugar, cocoa, peanuts
"""


async def fake_ocr_success(image_bytes: bytes, content_type: str) -> OcrResult:
    return OcrResult(text=OCR_TEXT, confidence=0.8, provider="test")


def post_analyse(client, headers, image_path, question="Is this safe for me?"):
    with open(image_path, "rb") as image:
        return client.post(
            "/api/v1/analyse",
            headers=headers,
            data={"question": question},
            files={"image": ("label.png", image, "image/png")},
        )


def test_analyse_success_with_profile_persists_chat(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_analyse(client, auth_headers, image_file)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"session_id", "nutrition", "answer", "confidence"}
    assert payload["nutrition"]["calories"] == 220.0
    assert payload["nutrition"]["sugar_g"] == 18.0
    assert "peanuts" in payload["nutrition"]["ingredients"]
    assert payload["answer"]["summary"]
    assert isinstance(payload["answer"]["recommendations"], list)
    assert isinstance(payload["answer"]["warnings"], list)
    assert payload["confidence"] > 0

    assert asyncio.run(fetch_chat_counts()) == (1, 2)


def test_analyse_missing_profile_returns_409(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    register_user(client, auth_headers)

    response = post_analyse(client, auth_headers, image_file)

    assert response.status_code == 409
    assert "health profile" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_analyse_invalid_image_returns_400(client, auth_headers):
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = client.post(
        "/api/v1/analyse",
        headers=auth_headers,
        data={"question": "Is this ok?"},
        files={"image": ("not-image.txt", b"not image bytes", "text/plain")},
    )

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_analyse_ocr_failure_returns_502(client, auth_headers, image_file, monkeypatch):
    async def fail_ocr(image_bytes: bytes, content_type: str):
        raise OcrServiceError("OCR service timed out. Please try again.")

    monkeypatch.setattr("app.services.ocr_service.extract_text", fail_ocr)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_analyse(client, auth_headers, image_file)

    assert response.status_code == 502
    assert "ocr" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_analyse_inference_fallback_path(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    monkeypatch.setattr(
        "app.services.inference_client.get_settings",
        lambda: fake_settings(inference_service_url="http://127.0.0.1:9/infer"),
    )
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_analyse(client, auth_headers, image_file)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer"]["summary"]
    assert any("fallback" in warning.lower() for warning in payload["answer"]["warnings"])
    assert payload["confidence"] <= 0.45
    assert asyncio.run(fetch_chat_counts()) == (1, 2)


def test_analyse_question_too_long_returns_422(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr("app.services.ocr_service.extract_text", fake_ocr_success)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_analyse(client, auth_headers, image_file, question="x" * 1001)

    assert response.status_code == 422
    assert "question" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)
