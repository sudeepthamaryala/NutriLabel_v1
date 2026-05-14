import argparse
import asyncio
from pathlib import Path

from app.core.database import get_sessionmaker
from app.services.knowledge_ingestion import ingest_week3_rag


async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Week 3 disease and reference PDF RAG corpora.")
    parser.add_argument(
        "--reference-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "reference",
        help="Directory containing the required Week 3 reference PDFs.",
    )
    args = parser.parse_args()

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as db:
        result = await ingest_week3_rag(db=db, reference_dir=args.reference_dir)

    print(
        "Ingested "
        f"{result['disease_knowledge_chunks']} disease_knowledge_chunks and "
        f"{result['knowledge_chunks']} knowledge_chunks."
    )


if __name__ == "__main__":
    asyncio.run(main())
