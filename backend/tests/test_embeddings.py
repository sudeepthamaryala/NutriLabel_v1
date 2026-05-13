from app.core.embeddings import embed_text
import pytest


def test_embed_text_returns_384_vector():
    vector = embed_text("Low sugar breakfast options")

    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(item, float) for item in vector)


def test_embed_text_empty_returns_empty_list():
    with pytest.raises(ValueError):
        embed_text("   ")
