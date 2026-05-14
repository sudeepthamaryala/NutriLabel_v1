from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user, get_request_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.compare import CompareResponse
from app.services.compare_service import compare_images
from app.services.input_validation import validate_compare_images, validate_question

router = APIRouter(prefix="/compare", tags=["compare"])


@router.post("", response_model=CompareResponse)
async def compare(
    images: Annotated[list[UploadFile], File(...)],
    question: Annotated[str | None, Form()] = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> CompareResponse:
    validate_compare_images(images)
    cleaned_question = validate_question(question)
    return await compare_images(
        db=db,
        current_user=current_user,
        images=images,
        question=cleaned_question,
        request_id=request_id,
    )
