import logging

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.compare import ComparedProduct, CompareResponse, CompareVerdict
from app.services import chat_service, storage_service
from app.services.analyse_service import get_required_health_profile, ocr_and_parse_nutrition
from app.services.inference_client import CompareInferenceResult, compare_nutrition_products

logger = logging.getLogger(__name__)


async def compare_images(
    *,
    db: AsyncSession,
    current_user: User,
    images: list[UploadFile],
    question: str | None,
    request_id: str,
) -> CompareResponse:
    profile = await get_required_health_profile(db=db, current_user=current_user)

    products: list[ComparedProduct] = []
    ocr_metadata: list[dict] = []
    parsed_images = []
    for index, image in enumerate(images):
        parsed = await ocr_and_parse_nutrition(image=image, request_id=request_id)
        parsed_images.append(parsed)
        products.append(ComparedProduct(index=index, nutrition=parsed.nutrition))
        ocr_metadata.append(
            {
                "index": index,
                "filename": parsed.filename,
                "provider": parsed.ocr_result.provider,
                "confidence": parsed.ocr_result.confidence,
                "text": parsed.ocr_result.text,
            }
        )

    comparison = await _compare_with_inference(
        products=products,
        profile=profile,
        question=question,
        request_id=request_id,
    )
    user_content = question.strip() if question and question.strip() else "Compare products"
    assistant_content = _assistant_content(comparison.verdict)
    stored_images = await _store_images_after_success(
        parsed_images=parsed_images,
        user_id=str(current_user.id),
        request_id=request_id,
    )

    try:
        session = await chat_service.create_compare_session(
            db=db,
            user_id=current_user.id,
            question=question,
            user_content=user_content,
            assistant_content=assistant_content,
            metadata={
                "request_id": request_id,
                "image_count": len(images),
                "image_storage_paths": [image.path for image in stored_images],
                "image_urls": [image.public_url for image in stored_images],
                "products": [product.model_dump() for product in products],
                "best_product_index": comparison.best_product_index,
                "verdict": comparison.verdict.model_dump(),
                "used_fallback": comparison.used_fallback,
                "ocr": ocr_metadata,
            },
        )
    except SQLAlchemyError as exc:
        logger.exception("compare_chat_persistence_failed request_id=%s", request_id)
        for stored_image in stored_images:
            await storage_service.cleanup_image(stored_image.path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Comparison completed but could not be saved. Please try again.",
        ) from exc

    return CompareResponse(
        session_id=session.id,
        products=products,
        best_product_index=comparison.best_product_index,
        verdict=comparison.verdict,
    )


async def _compare_with_inference(
    *,
    products: list[ComparedProduct],
    profile,
    question: str | None,
    request_id: str,
) -> CompareInferenceResult:
    try:
        return await compare_nutrition_products(
            products=products,
            profile=profile,
            question=question,
        )
    except Exception as exc:
        logger.exception("compare_inference_failed request_id=%s", request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Inference service is unavailable.",
        ) from exc


def _assistant_content(verdict: CompareVerdict) -> str:
    details = "; ".join(verdict.reasons) if verdict.reasons else "No detailed reasons available."
    return f"{verdict.best_product} is recommended. {details}"


async def _store_images_after_success(*, parsed_images: list, user_id: str, request_id: str):
    stored_images = []
    for parsed_image in parsed_images:
        try:
            stored_image = await storage_service.upload_image(
                image_bytes=parsed_image.content,
                content_type=parsed_image.content_type,
                user_id=user_id,
            )
        except storage_service.StorageServiceError:
            logger.warning("compare_storage_upload_failed request_id=%s", request_id)
            continue
        if stored_image:
            stored_images.append(stored_image)
    return stored_images
