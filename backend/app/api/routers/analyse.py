from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user, get_request_id
from app.core.database import get_db
from app.models.user import User
from app.schemas.analyse import AnalyseResponse
from app.services.analyse_service import analyse_image
from app.services.input_validation import validate_image_metadata, validate_question

router = APIRouter(prefix="/analyse", tags=["analyse"])


@router.post("", response_model=AnalyseResponse)
async def analyse(
    image: Annotated[UploadFile, File(...)],
    question: Annotated[str | None, Form()] = None,
    current_user: User | None = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
    request_id: str = Depends(get_request_id),
) -> AnalyseResponse:
    validate_image_metadata(image)
    cleaned_question = validate_question(question)
    return await analyse_image(
        db=db,
        current_user=current_user,
        image=image,
        question=cleaned_question,
        request_id=request_id,
    )
