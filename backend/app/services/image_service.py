from dataclasses import dataclass

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    content: bytes
    content_type: str
    filename: str | None


ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
UNSPECIFIED_CONTENT_TYPES = {"", "application/octet-stream"}


async def validate_upload(file: UploadFile) -> ValidatedImage:
    validate_upload_metadata(file)
    content = await file.read()
    detected_content_type = validate_image_bytes(content, expected_content_type=file.content_type or "")
    return ValidatedImage(content=content, content_type=detected_content_type, filename=file.filename)


def validate_upload_metadata(file: UploadFile) -> None:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_CONTENT_TYPES and content_type not in UNSPECIFIED_CONTENT_TYPES:
        raise ImageValidationError("Image must be JPEG, PNG, or WEBP.")


def validate_image_bytes(content: bytes, expected_content_type: str | None = None) -> str:
    from app.core.settings import get_settings

    if not content:
        raise ImageValidationError("Image file is empty.")
    if len(content) > get_settings().max_upload_bytes:
        raise ImageValidationError("Image is too large.")

    try:
        from io import BytesIO

        with Image.open(BytesIO(content)) as image:
            detected_content_type = Image.MIME.get(image.format or "")
            if detected_content_type not in ALLOWED_CONTENT_TYPES:
                raise ImageValidationError("Image must be JPEG, PNG, or WEBP.")
            if (
                expected_content_type
                and expected_content_type not in UNSPECIFIED_CONTENT_TYPES
                and detected_content_type != expected_content_type
            ):
                raise ImageValidationError("Image content does not match the declared MIME type.")
            image.verify()
            return detected_content_type
    except (UnidentifiedImageError, OSError):
        raise ImageValidationError("Uploaded file is not a valid image.")
