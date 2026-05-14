from pathlib import Path
import re

from sqlalchemy.ext.asyncio import AsyncSession

from app.data.disease_corpus import disease_chunks
from app.services.rag_service import store_disease_knowledge_chunks, store_knowledge_chunks

REFERENCE_PDFS = {
    "who_healthy_diet.pdf": "WHO healthy diet",
    "fda_daily_value.pdf": "FDA daily value",
    "fda_nutrition_label_understanding.pdf": "FDA nutrition label understanding",
    "icmr_diet_guidelines.pdf": "ICMR dietary guidelines",
}


async def ingest_week3_rag(*, db: AsyncSession, reference_dir: Path) -> dict[str, int]:
    disease_count = await store_disease_knowledge_chunks(db=db, chunks=disease_chunks(), replace=True)
    pdf_chunks = extract_reference_pdf_chunks(reference_dir=reference_dir)
    knowledge_count = await store_knowledge_chunks(
        db=db,
        chunks=pdf_chunks,
        replace_sources={item["source"] for item in pdf_chunks},
    )
    return {"disease_knowledge_chunks": disease_count, "knowledge_chunks": knowledge_count}


def extract_reference_pdf_chunks(*, reference_dir: Path, approx_tokens: int = 300) -> list[dict]:
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF is required for reference PDF ingestion.") from exc

    chunks: list[dict] = []
    for filename, source in REFERENCE_PDFS.items():
        pdf_path = reference_dir / filename
        if not pdf_path.exists():
            raise FileNotFoundError(f"Required reference PDF is missing: {pdf_path}")

        with fitz.open(pdf_path) as document:
            for page_index, page in enumerate(document, start=1):
                page_text = _normalize_text(page.get_text("text"))
                for chunk_index, chunk_text in enumerate(_chunk_text(page_text, approx_tokens), start=1):
                    chunks.append(
                        {
                            "source": source,
                            "source_url": str(pdf_path),
                            "page_number": page_index,
                            "chunk_text": (
                                f"Source: {source}. Page: {page_index}. "
                                f"Evidence: {chunk_text}"
                            ),
                            "metadata": {
                                "filename": filename,
                                "page_number": page_index,
                                "chunk_index": chunk_index,
                                "corpus": "week3_reference_pdfs",
                            },
                        }
                    )
    return chunks


def _chunk_text(text: str, approx_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []

    stride = max(approx_tokens - 45, 1)
    chunks: list[str] = []
    for start in range(0, len(words), stride):
        piece = words[start : start + approx_tokens]
        if len(piece) < 45 and chunks:
            chunks[-1] = chunks[-1] + " " + " ".join(piece)
        else:
            chunks.append(" ".join(piece))
    return chunks


def _normalize_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"([a-z])-\s+([a-z])", r"\1\2", text, flags=re.IGNORECASE)
    return text.strip()
