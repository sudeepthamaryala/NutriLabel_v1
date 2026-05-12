from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.services import storage_service
from app.services.image_service import ImageValidationError, validate_upload

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/image")
async def upload_image(
    image: Annotated[UploadFile, File(...)],
) -> dict:
    try:
        validated = await validate_upload(image)
        stored = await storage_service.upload_image(
            image_bytes=validated.content,
            content_type=validated.content_type,
            user_id="development",
        )
    except ImageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except storage_service.StorageServiceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if stored is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Supabase Storage is not enabled")

    return {"url": stored.public_url, "path": stored.path}
