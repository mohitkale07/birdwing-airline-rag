import json
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np
from docling.document_converter import DocumentConverter

from src.ingestion.chunker import TextChunk, chunk_docling_document
from src.ingestion.embedder import generate_embeddings

from src.ingestion.docling_extractor import convert_pdf_with_docling

logger = logging.getLogger(__name__)

DOCUMENT_ACCESS = {
    "birdwing_cx_operations_manual.pdf": (
        "customer_service",
        ["support_agent", "admin"],
    ),
    "birdwing_people_policy_handbook.pdf": (
        "hr",
        ["hr", "admin", "employee"],
    ),
    # An empty role list means this source is available without authentication.
    "birdwing_public_conditions_of_carriage.pdf": ("public", []),
}


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]
    raw_dir = project_root / "data" / "raw"
    output_dir = project_root / "data" / "processed"

    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_paths = sorted(
        (
            path
            for path in raw_dir.iterdir()
            if path.is_file() and path.suffix.lower() == ".pdf"
        ),
        key=lambda path: path.name.casefold(),
    )
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF files found in {raw_dir}")

    missing_access = [
        path.name for path in pdf_paths if path.name not in DOCUMENT_ACCESS
    ]
    if missing_access:
        raise ValueError(
            "Add source and allowed_roles metadata in DOCUMENT_ACCESS for: "
            + ", ".join(missing_access)
        )

    converter = DocumentConverter()
    chunks: list[TextChunk] = []
    total_pages = 0

    for pdf_path in pdf_paths:
        source, allowed_roles = DOCUMENT_ACCESS[pdf_path.name]
        document = convert_pdf_with_docling(pdf_path, converter=converter)
        total_pages += len(document.pages)
        chunks.extend(
            chunk_docling_document(
                document,
                document_name=pdf_path.name,
                source=source,
                allowed_roles=allowed_roles,
            )
        )

    if not chunks:
        raise ValueError(f"Chunking produced no chunks from PDFs in {raw_dir}")

    # Embed all files together so each matrix row stays aligned with its chunk.
    result = generate_embeddings(chunks)

    # Save text and access metadata in the same row order as the embedding matrix.
    chunks_path = output_dir / "chunks.json"
    with chunks_path.open("w", encoding="utf-8") as file:
        json.dump(
            [asdict(chunk) for chunk in result.chunks],
            file,
            ensure_ascii=False,
            indent=2,
        )

    # Save vectors separately as a NumPy array.
    embeddings_path = output_dir / "embeddings.npy"
    np.save(embeddings_path, result.embeddings)

    logger.info("PDF files processed: %d", len(pdf_paths))
    logger.info("Pages extracted: %d", total_pages)
    logger.info("Chunks created: %d", len(result.chunks))
    logger.info("Embedding dimensions: %d", result.embeddings.shape[1])
    logger.info("Embedding shape: %s", result.embeddings.shape)
    logger.info("Chunks saved to: %s", chunks_path)
    logger.info("Embeddings saved to: %s", embeddings_path)


if __name__ == "__main__":
    main()
