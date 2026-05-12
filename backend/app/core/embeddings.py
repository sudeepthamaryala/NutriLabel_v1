from functools import lru_cache
from typing import List

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384


@lru_cache(maxsize=1)
def _get_embedding_model():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError(
            "Local embeddings are unavailable. Install sentence-transformers "
            "or configure EMBEDDING_SERVICE_URL."
        ) from exc

    return SentenceTransformer(MODEL_NAME, device="cpu")


def embed_text(text: str) -> List[float]:
    if text is None:
        raise ValueError("text must be a non-empty string")

    cleaned = text.strip()
    if not cleaned:
        return []

    model = _get_embedding_model()
    embeddings = model.encode([cleaned], show_progress_bar=False, convert_to_numpy=True)

    if embeddings.shape != (1, EMBEDDING_DIMENSIONS):
        raise RuntimeError(
            f"unexpected embedding shape: {embeddings.shape}, expected (1, {EMBEDDING_DIMENSIONS})"
        )

    return [float(value) for value in embeddings[0].tolist()]
