from dataclasses import dataclass
from uuid import uuid4

import httpx

from app.core.retry import retry_async
from app.core.settings import get_settings


class StorageServiceError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    path: str
    public_url: str
    signed_url: str | None


async def upload_image(
    *,
    image_bytes: bytes,
    content_type: str,
    user_id: str,
) -> StoredImage | None:
    settings = get_settings()
    if not settings.storage_enabled:
        return None
    _validate_storage_settings(settings)

    extension = _extension_for(content_type)
    path = f"{user_id}/{uuid4()}{extension}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key or "",
        "Content-Type": content_type,
        "x-upsert": "false",
    }
    object_url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}/{path}"

    async def post_object() -> httpx.Response:
        async with httpx.AsyncClient(timeout=settings.external_service_timeout_seconds) as client:
            response = await client.post(object_url, headers=headers, content=image_bytes)
            response.raise_for_status()
            return response

    try:
        await retry_async(post_object, retries=settings.external_retry_attempts)
        signed_url = await create_signed_url(path)
        return StoredImage(path=path, public_url=public_url(path), signed_url=signed_url)
    except httpx.HTTPError as exc:
        raise StorageServiceError("Image storage upload failed.") from exc


async def create_signed_url(path: str) -> str | None:
    settings = get_settings()
    if not settings.storage_enabled:
        return None

    _validate_storage_settings(settings)
    url = f"{settings.supabase_url}/storage/v1/object/sign/{settings.supabase_storage_bucket}/{path}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key or "",
    }

    async def sign_object() -> httpx.Response:
        async with httpx.AsyncClient(timeout=settings.external_service_timeout_seconds) as client:
            response = await client.post(
                url,
                headers=headers,
                json={"expiresIn": settings.storage_signed_url_ttl_seconds},
            )
            response.raise_for_status()
            return response

    try:
        response = await retry_async(sign_object, retries=settings.external_retry_attempts)
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise StorageServiceError("Image signed URL creation failed.") from exc

    signed = payload.get("signedURL") or payload.get("signedUrl")
    if not signed:
        return None
    if str(signed).startswith("http"):
        return str(signed)
    return f"{settings.supabase_url}/storage/v1{signed}"


async def cleanup_image(path: str | None) -> None:
    settings = get_settings()
    if not path or not settings.storage_enabled:
        return
    _validate_storage_settings(settings)

    url = f"{settings.supabase_url}/storage/v1/object/{settings.supabase_storage_bucket}"
    headers = {
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "apikey": settings.supabase_service_role_key or "",
    }
    try:
        async with httpx.AsyncClient(timeout=settings.external_service_timeout_seconds) as client:
            await client.request("DELETE", url, headers=headers, json={"prefixes": [path]})
    except httpx.HTTPError:
        return


def _validate_storage_settings(settings) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key or not settings.supabase_storage_bucket:
        raise StorageServiceError("Supabase Storage is enabled but not fully configured.")


def public_url(path: str) -> str:
    settings = get_settings()
    _validate_storage_settings(settings)
    return f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/{settings.supabase_storage_bucket}/{path}"


def _extension_for(content_type: str) -> str:
    return {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }.get(content_type, "")
