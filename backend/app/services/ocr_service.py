from dataclasses import dataclass
from io import BytesIO
import logging

import anyio
import httpx
from PIL import Image, UnidentifiedImageError

from app.core.settings import get_settings
from app.services.image_service import ALLOWED_CONTENT_TYPES, validate_image_bytes

logger = logging.getLogger(__name__)


class OcrServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class OcrResult:
    text: str
    confidence: float
    provider: str


async def extract_text_from_url(image_url: str) -> OcrResult:
    image_bytes, content_type = await download_image(image_url)
    return await extract_text(image_bytes, content_type)


async def download_image(image_url: str) -> tuple[bytes, str]:
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=settings.external_service_timeout_seconds, follow_redirects=True) as client:
            response = await client.get(image_url)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise OcrServiceError("Image download timed out.") from exc
    except httpx.HTTPError as exc:
        raise OcrServiceError("Image download failed.") from exc

    content_type = response.headers.get("content-type", "").split(";")[0].lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise OcrServiceError("Image URL must point to JPEG, PNG, or WEBP.")

    image_bytes = response.content
    try:
        validate_image_bytes(image_bytes)
    except ValueError as exc:
        raise OcrServiceError(str(exc)) from exc
    return image_bytes, content_type


async def extract_text(image_bytes: bytes, content_type: str) -> OcrResult:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise OcrServiceError("Image must be JPEG, PNG, or WEBP.")

    try:
        validate_image_bytes(image_bytes)
    except ValueError as exc:
        raise OcrServiceError(str(exc)) from exc

    try:
        return await _extract_with_google_vision(image_bytes)
    except Exception as exc:
        logger.warning("google_vision_ocr_failed fallback=tesseract error=%s", exc)
        return await _extract_with_tesseract(image_bytes)


async def _extract_with_google_vision(image_bytes: bytes) -> OcrResult:
    settings = get_settings()

    def run_google_vision() -> OcrResult:
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        response = client.text_detection(image=vision.Image(content=image_bytes))
        if response.error.message:
            raise OcrServiceError(response.error.message)
        annotations = response.text_annotations
        text = annotations[0].description.strip() if annotations else ""
        if not text:
            raise OcrServiceError("OCR could not read text from the image.")
        return OcrResult(text=text, confidence=0.85, provider="google_vision")

    try:
        with anyio.fail_after(settings.external_service_timeout_seconds):
            return await anyio.to_thread.run_sync(run_google_vision)
    except TimeoutError as exc:
        raise OcrServiceError("Google Vision OCR timed out.") from exc


async def _extract_with_tesseract(image_bytes: bytes) -> OcrResult:
    settings = get_settings()
    try:
        with anyio.fail_after(settings.external_service_timeout_seconds):
            text = await anyio.to_thread.run_sync(_run_tesseract, image_bytes)
    except TimeoutError as exc:
        raise OcrServiceError("Tesseract OCR timed out.") from exc
    except Exception as exc:
        raise OcrServiceError("OCR failed while reading the image.") from exc

    if not text:
        raise OcrServiceError("OCR could not read text from the image.")
    return OcrResult(text=text, confidence=0.70, provider="tesseract")


def _run_tesseract(image_bytes: bytes) -> str:
    import pytesseract

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            return pytesseract.image_to_string(image).strip()
    except (UnidentifiedImageError, OSError) as exc:
        raise OcrServiceError("Uploaded file is not a valid image.") from exc
