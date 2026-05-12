import asyncio

from app.services.ocr_service import OcrResult, OcrServiceError

from conftest import create_profile, fake_settings, fetch_chat_counts, register_user


HIGH_SUGAR_TEXT = """
Nutrition Facts
Serving size 45g
Calories 240
Total Fat 8g
Sodium 380mg
Total Sugars 22g
Protein 5g
Ingredients: oats, sugar, cocoa
"""

LOW_SUGAR_TEXT = """
Nutrition Facts
Serving size 45g
Calories 190
Total Fat 7g
Sodium 260mg
Total Sugars 5g
Protein 8g
Ingredients: oats, almonds, cocoa
"""


def fake_ocr_sequence(*texts: str):
    remaining = list(texts)

    async def fake_ocr(image_bytes: bytes, content_type: str) -> OcrResult:
        text = remaining.pop(0) if remaining else texts[-1]
        return OcrResult(text=text, confidence=0.8, provider="test")

    return fake_ocr


def post_compare(client, headers, image_path, question="Which one is better?"):
    with open(image_path, "rb") as first, open(image_path, "rb") as second:
        return client.post(
            "/api/v1/compare",
            headers=headers,
            data={"question": question},
            files=[
                ("images", ("first.png", first, "image/png")),
                ("images", ("second.png", second, "image/png")),
            ],
        )


def test_compare_success_with_two_images_persists_chat(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr(
        "app.services.ocr_service.extract_text",
        fake_ocr_sequence(HIGH_SUGAR_TEXT, LOW_SUGAR_TEXT),
    )
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_compare(client, auth_headers, image_file)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload) == {"session_id", "products", "best_product_index", "verdict"}
    assert len(payload["products"]) == 2
    assert payload["best_product_index"] == 1
    assert payload["verdict"]["best_product"] == "Product 2"
    assert payload["verdict"]["reasons"]
    assert asyncio.run(fetch_chat_counts()) == (1, 2)


def test_compare_invalid_image_returns_400(client, auth_headers, image_file):
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    with open(image_file, "rb") as valid:
        response = client.post(
            "/api/v1/compare",
            headers=auth_headers,
            data={"question": "Compare these"},
            files=[
                ("images", ("valid.png", valid, "image/png")),
                ("images", ("bad.txt", b"not image bytes", "text/plain")),
            ],
        )

    assert response.status_code == 400
    assert "image" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_compare_too_few_images_returns_400(client, auth_headers, image_file):
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    with open(image_file, "rb") as image:
        response = client.post(
            "/api/v1/compare",
            headers=auth_headers,
            data={"question": "Compare these"},
            files=[("images", ("single.png", image, "image/png"))],
        )

    assert response.status_code == 400
    assert "at least 2" in response.json()["detail"]
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_compare_ocr_failure_returns_502(client, auth_headers, image_file, monkeypatch):
    async def fail_ocr(image_bytes: bytes, content_type: str):
        raise OcrServiceError("OCR service timed out. Please try again.")

    monkeypatch.setattr("app.services.ocr_service.extract_text", fail_ocr)
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_compare(client, auth_headers, image_file)

    assert response.status_code == 502
    assert "ocr" in response.json()["detail"].lower()
    assert asyncio.run(fetch_chat_counts()) == (0, 0)


def test_compare_inference_fallback_path(client, auth_headers, image_file, monkeypatch):
    monkeypatch.setattr(
        "app.services.ocr_service.extract_text",
        fake_ocr_sequence(HIGH_SUGAR_TEXT, LOW_SUGAR_TEXT),
    )
    monkeypatch.setattr(
        "app.services.inference_client.get_settings",
        lambda: fake_settings(inference_service_url="http://127.0.0.1:9/infer"),
    )
    register_user(client, auth_headers)
    create_profile(client, auth_headers)

    response = post_compare(client, auth_headers, image_file)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["best_product_index"] == 1
    assert any("fallback" in warning.lower() for warning in payload["verdict"]["warnings"])
    assert asyncio.run(fetch_chat_counts()) == (1, 2)

