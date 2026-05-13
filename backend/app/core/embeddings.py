from functools import lru_cache
import logging
from typing import List

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        logger.exception("sentence_transformers_import_failed")
        raise RuntimeError(f"Local embeddings are unavailable: {exc}") from exc

    try:
        return SentenceTransformer(MODEL_NAME, device="cpu")
    except Exception as exc:
        logger.exception("sentence_transformer_load_failed model=%s", MODEL_NAME)
        raise RuntimeError(f"Local embedding model failed to load: {exc}") from exc


def embed_text(text: str) -> List[float]:
    if text is None:
        raise ValueError("text must be a non-empty string")

    cleaned = text.strip()
    if not cleaned:
        raise ValueError("text must be a non-empty string")

    model = _get_embedding_model()
    embeddings = model.encode([cleaned], show_progress_bar=False, convert_to_numpy=True)

    if embeddings.shape != (1, EMBEDDING_DIMENSIONS):
        raise RuntimeError(
            f"unexpected embedding shape: {embeddings.shape}, expected (1, {EMBEDDING_DIMENSIONS})"
        )

    return [float(value) for value in embeddings[0].tolist()]
