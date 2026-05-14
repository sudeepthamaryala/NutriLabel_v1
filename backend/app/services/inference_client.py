from dataclasses import dataclass
from decimal import Decimal
import logging

import httpx

from app.core.retry import retry_async
from app.core.settings import get_settings
from app.models.health_profile import HealthProfile
from app.schemas.analyse import AnalyseAnswer, NutritionData
from app.schemas.compare import ComparedProduct, CompareVerdict

logger = logging.getLogger(__name__)


class InferenceClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class InferenceResult:
    answer: AnalyseAnswer
    confidence: float


@dataclass(frozen=True)
class CompareInferenceResult:
    best_product_index: int
    verdict: CompareVerdict
    used_fallback: bool = False


async def analyse_nutrition(
    *,
    nutrition: NutritionData,
    profile: HealthProfile,
    question: str | None,
    rag_context: dict,
    prompt: str,
) -> InferenceResult:
    settings = get_settings()
    if settings.inference_service_url:
        try:
            return await _call_external_inference(
                url=settings.inference_service_url,
                timeout=settings.external_service_timeout_seconds,
                retries=settings.external_retry_attempts,
                nutrition=nutrition,
                profile=profile,
                question=question,
                rag_context=rag_context,
                prompt=prompt,
            )
        except InferenceClientError:
            logger.warning("inference_failed reason=external_failure")
            raise

    raise InferenceClientError("INFERENCE_SERVICE_URL is not configured.")


async def compare_nutrition_products(
    *,
    products: list[ComparedProduct],
    profile: HealthProfile,
    question: str | None,
) -> CompareInferenceResult:
    settings = get_settings()
    if settings.inference_service_url:
        try:
            return await _call_external_compare(
                url=settings.inference_service_url,
                timeout=settings.external_service_timeout_seconds,
                retries=settings.external_retry_attempts,
                products=products,
                profile=profile,
                question=question,
            )
        except InferenceClientError:
            logger.warning("compare_inference_failed reason=external_failure")
            raise

    raise InferenceClientError("INFERENCE_SERVICE_URL is not configured.")


async def _call_external_inference(
    *,
    url: str,
    timeout: float,
    retries: int,
    nutrition: NutritionData,
    profile: HealthProfile,
    question: str | None,
    rag_context: dict,
    prompt: str,
) -> InferenceResult:
    payload = {
        "task": "analyse",
        "nutrition": nutrition.model_dump(),
        "profile": _profile_payload(profile),
        "question": question,
        "rag_context": rag_context,
        "prompt": prompt,
    }
    async def request_inference() -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response

    try:
        response = await retry_async(request_inference, retries=retries)
        data = response.json()
    except httpx.TimeoutException as exc:
        raise InferenceClientError("Inference service timed out.") from exc
    except httpx.HTTPError as exc:
        raise InferenceClientError("Inference service failed.") from exc

    if not isinstance(data, dict):
        raise InferenceClientError("Inference service returned an invalid response.")

    answer_data = data.get("answer") or data
    answer = AnalyseAnswer(
        summary=str(answer_data.get("summary") or "Analysis completed."),
        recommendations=list(answer_data.get("recommendations") or []),
        warnings=list(answer_data.get("warnings") or []),
    )
    confidence = float(data.get("confidence") or 0.75)
    return InferenceResult(answer=answer, confidence=max(0.0, min(confidence, 1.0)))


def _profile_payload(profile: HealthProfile) -> dict:
    return {
        "age": profile.age,
        "weight_kg": _decimal_to_float(profile.weight_kg),
        "height_cm": _decimal_to_float(profile.height_cm),
        "sex": profile.sex.value,
        "activity_level": profile.activity_level.value,
        "goal": profile.goal.value,
        "allergies": profile.allergies,
        "diseases": profile.diseases,
        "dietary_preferences": profile.dietary_preferences,
    }


def _decimal_to_float(value: Decimal) -> float:
    return float(value)


async def _call_external_compare(
    *,
    url: str,
    timeout: float,
    retries: int,
    products: list[ComparedProduct],
    profile: HealthProfile,
    question: str | None,
) -> CompareInferenceResult:
    payload = {
        "task": "compare",
        "products": [product.model_dump() for product in products],
        "profile": _profile_payload(profile),
        "question": question,
    }
    async def request_compare() -> httpx.Response:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response

    try:
        response = await retry_async(request_compare, retries=retries)
        data = response.json()
    except httpx.TimeoutException as exc:
        raise InferenceClientError("Comparison inference service timed out.") from exc
    except httpx.HTTPError as exc:
        raise InferenceClientError("Comparison inference service failed.") from exc

    if not isinstance(data, dict):
        raise InferenceClientError("Comparison inference service returned an invalid response.")

    verdict_data = data.get("verdict") or {}
    best_index = int(data.get("best_product_index", 0))
    if best_index < 0 or best_index >= len(products):
        raise InferenceClientError("Comparison inference returned an invalid product index.")

    return CompareInferenceResult(
        best_product_index=best_index,
        verdict=CompareVerdict(
            best_product=str(verdict_data.get("best_product") or f"Product {best_index + 1}"),
            reasons=list(verdict_data.get("reasons") or []),
            tradeoffs=list(verdict_data.get("tradeoffs") or []),
            warnings=list(verdict_data.get("warnings") or []),
        ),
    )
