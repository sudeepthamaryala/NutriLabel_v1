from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routers import analyse, auth, chat, compare, embedding, health, profile, uploads
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware, RequestSizeLimitMiddleware
from app.core.settings import get_settings, validate_startup_settings
from app.schemas.common import HealthResponse

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    validate_startup_settings(settings)
    logger.info("startup_config_validated app=%s", settings.app_name)
    
    app.state.redis = None
    if settings.redis_url:
        try:
            from redis.asyncio import Redis
            app.state.redis = Redis.from_url(settings.redis_url, decode_responses=True)
            logger.info("redis_pool_initialized")
        except Exception as e:
            logger.warning("failed to initialize redis: %s", e)

    # it does NOT block the event loop — but it is significantly slower than a
    # dedicated OCR microservice and exhausts the default thread-pool under load.
    logger.info("ocr_provider=google_vision fallback=pytesseract")

    yield

    if getattr(app.state, "redis", None):
        await app.state.redis.aclose()
        logger.info("redis_pool_closed")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        # allow_origins=settings.cors_origins,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)

    prefix = settings.api_v1_prefix
    app.include_router(health.router, prefix=prefix)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(profile.router, prefix=prefix)
    app.include_router(analyse.router, prefix=prefix)
    app.include_router(compare.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(embedding.router, prefix=prefix)
    app.include_router(uploads.router, prefix=prefix)

    @app.get("/health", response_model=HealthResponse, include_in_schema=False)
    async def root_health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
