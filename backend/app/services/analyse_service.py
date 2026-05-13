import logging
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.enums import RagSourceType
from app.schemas.analyse import AnalyseResponse
from app.services import chat_service, nutrition_parser, ocr_service, rag_service, storage_service
from app.services.image_service import ImageValidationError, validate_upload
from app.services.inference_client import InferenceResult, analyse_nutrition
from app.services.profile_service import get_profile_for_user

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParsedNutritionImage:
    nutrition: object
    ocr_result: object
    filename: str | None
    content: bytes
    content_type: str


async def analyse_image(
    *,
    db: AsyncSession,
    current_user: User,
    image: UploadFile,
    question: str | None,
    request_id: str,
) -> AnalyseResponse:
    """Run label analysis using in-memory image bytes.

    Storage mode should upload only after OCR + inference succeed, or upload to a
    temporary key and delete it on any exception before chat persistence commits.
    This keeps failed analyses from leaving orphaned storage artifacts.
    """
    profile = await get_required_health_profile(db=db, current_user=current_user)
    parsed_image = await ocr_and_parse_nutrition(
        image=image,
        request_id=request_id,
    )
    nutrition = parsed_image.nutrition
    ocr_result = parsed_image.ocr_result
    await _embed_label_chunk(
        db=db,
        user_id=current_user.id,
        ocr_text=ocr_result.text,
        nutrition=nutrition.model_dump(),
        request_id=request_id,
    )

    rag_context = await rag_service.retrieve_relevant_chunks(
        db=db,
        question=question,
        nutrition=nutrition,
    )
    inference = await _analyse_with_inference(
        nutrition=nutrition,
        profile=profile,
        question=question,
        rag_context=rag_context,
        request_id=request_id,
    )

    confidence = min(inference.confidence, ocr_result.confidence)
    assistant_content = inference.answer.summary
    user_content = question.strip() if question and question.strip() else "Analyse this nutrition label."
    stored_image = await _store_image_after_success(
        image_bytes=parsed_image.content,
        content_type=parsed_image.content_type,
        user_id=str(current_user.id),
        request_id=request_id,
    )
    try:
        session = await chat_service.create_analyse_session(
            db=db,
            user_id=current_user.id,
            question=question,
            user_content=user_content,
            assistant_content=assistant_content,
            image_url=stored_image.public_url if stored_image else None,
            metadata={
                "filename": parsed_image.filename,
                "nutrition": nutrition.model_dump(),
                "answer": inference.answer.model_dump(),
                "confidence": confidence,
                "request_id": request_id,
                "image_storage_path": stored_image.path if stored_image else None,
                "ocr": {
                    "provider": ocr_result.provider,
                    "confidence": ocr_result.confidence,
                    "text": ocr_result.text,
                },
                "rag_context": rag_context,
            },
        )
    except SQLAlchemyError as exc:
        logger.exception("chat_persistence_failed request_id=%s", request_id)
        await storage_service.cleanup_image(stored_image.path if stored_image else None)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis completed but could not be saved. Please try again.",
        ) from exc

    return AnalyseResponse(
        session_id=session.id,
        nutrition=nutrition,
        answer=inference.answer,
        confidence=confidence,
    )


async def ocr_and_parse_nutrition(
    *,
    image: UploadFile,
    request_id: str,
) -> ParsedNutritionImage:
    validated_image = await _validate_image(image)
    ocr_result = await _extract_text(
        validated_image.content,
        validated_image.content_type,
        request_id=request_id,
    )
    nutrition = nutrition_parser.parse(ocr_result.text)
    return ParsedNutritionImage(
        nutrition=nutrition,
        ocr_result=ocr_result,
        filename=validated_image.filename,
        content=validated_image.content,
        content_type=validated_image.content_type,
    )


async def get_required_health_profile(*, db: AsyncSession, current_user: User):
    try:
        return await get_profile_for_user(db=db, user_id=current_user.id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Create your health profile before analysing images.",
            )
        raise


async def _validate_image(image: UploadFile):
    try:
        return await validate_upload(image)
    except ImageValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


async def _extract_text(image_bytes: bytes, content_type: str, request_id: str):
    try:
        return await ocr_service.extract_text(image_bytes, content_type)
    except ocr_service.OcrServiceError as exc:
        logger.warning("ocr_failed request_id=%s message=%s", request_id, str(exc))
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


async def _analyse_with_inference(
    *,
    nutrition,
    profile,
    question: str | None,
    rag_context: list[str],
    request_id: str,
) -> InferenceResult:
    try:
        return await analyse_nutrition(
            nutrition=nutrition,
            profile=profile,
            question=question,
            rag_context=rag_context,
        )
    except Exception as exc:
        logger.exception("inference_failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Inference service is unavailable.",
        ) from exc


async def _store_image_after_success(
    *,
    image_bytes: bytes,
    content_type: str,
    user_id: str,
    request_id: str,
):
    try:
        return await storage_service.upload_image(
            image_bytes=image_bytes,
            content_type=content_type,
            user_id=user_id,
        )
    except storage_service.StorageServiceError:
        logger.warning("storage_upload_failed request_id=%s", request_id)
        return None


async def _embed_label_chunk(*, db: AsyncSession, user_id, ocr_text: str, nutrition: dict, request_id: str) -> None:
    text = f"OCR label text:\n{ocr_text[:3000]}\nParsed nutrition: {nutrition}"
    try:
        await rag_service.embed_and_store_chunk(
            db=db,
            text=text,
            source_type=RagSourceType.label_ocr,
            user_id=user_id,
        )
    except Exception as exc:
        logger.exception("label_embedding_store_failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store label OCR embedding.",
        ) from exc
