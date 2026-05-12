from fastapi import HTTPException, UploadFile, status

from app.core.settings import get_settings
from app.services.image_service import ImageValidationError, validate_upload_metadata


def validate_question(question: str | None) -> str | None:
    if question is None:
        return None

    cleaned = question.strip()
    if not cleaned:
        return None

    settings = get_settings()
    if len(cleaned) > settings.max_question_chars:
        raise HTTPException(
            status_code=422,
            detail=f"Question must be {settings.max_question_chars} characters or fewer.",
        )

    if "\x00" in cleaned:
        raise HTTPException(
            status_code=422,
            detail="Question contains invalid characters.",
        )

    return cleaned


def validate_image_metadata(image: UploadFile) -> UploadFile:
    try:
        validate_upload_metadata(image)
    except ImageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return image


def validate_compare_images(images: list[UploadFile]) -> list[UploadFile]:
    settings = get_settings()
    if len(images) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Compare requires at least 2 images.",
        )
    if len(images) > settings.max_compare_images:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compare accepts at most {settings.max_compare_images} images.",
        )

    for image in images:
        validate_image_metadata(image)
    return images
