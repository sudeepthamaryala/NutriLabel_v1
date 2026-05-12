from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import JWTError, jwt
from pydantic import EmailStr, TypeAdapter, ValidationError

from app.core.settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)
email_adapter = TypeAdapter(EmailStr)


@dataclass(frozen=True)
class SupabaseClaims:
    user_id: str
    email: str
    role: str | None = None


def _credentials_error(detail: str = "Invalid or expired token") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_token_claims(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> SupabaseClaims:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_error("Missing bearer token")

    settings = get_settings()
    if not settings.supabase_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=[settings.supabase_jwt_algorithm],
            audience=settings.supabase_jwt_audience,
        )
    except JWTError:
        return await _verify_with_supabase_auth(credentials.credentials)

    subject = payload.get("sub")
    email = payload.get("email")
    if not subject or not email:
        raise _credentials_error("Token is missing required user claims")

    try:
        UUID(subject)
        parsed_email = email_adapter.validate_python(email)
    except (ValueError, ValidationError):
        raise _credentials_error("Token contains invalid user claims")

    return SupabaseClaims(
        user_id=subject,
        email=str(parsed_email),
        role=payload.get("role"),
    )


async def _verify_with_supabase_auth(token: str) -> SupabaseClaims:
    settings = get_settings()
    api_key = settings.supabase_anon_key or settings.supabase_service_role_key
    if not settings.supabase_url or not api_key:
        raise _credentials_error()

    url = settings.supabase_url.rstrip("/") + "/auth/v1/user"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                url,
                headers={
                    "apikey": api_key,
                    "Authorization": f"Bearer {token}",
                },
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError):
        raise _credentials_error()

    subject = payload.get("id") or payload.get("sub")
    email = payload.get("email")
    if not subject or not email:
        raise _credentials_error("Token is missing required user claims")

    try:
        UUID(subject)
        parsed_email = email_adapter.validate_python(email)
    except (ValueError, ValidationError):
        raise _credentials_error("Token contains invalid user claims")

    return SupabaseClaims(
        user_id=subject,
        email=str(parsed_email),
        role=payload.get("role") or "authenticated",
    )
