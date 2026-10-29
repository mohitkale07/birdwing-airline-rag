from dataclasses import dataclass

import numpy as np
from sentence_transformers import SentenceTransformer

from src.ingestion.chunker import TextChunk

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EXPECTED_DIMENSIONS = 384


@dataclass(frozen=True, slots=True)
class EmbeddedChunks:
    chunks: list[TextChunk]
    embeddings: np.ndarray


def generate_embeddings(
    chunks: list[TextChunk],
    batch_size: int = 32,
) -> EmbeddedChunks:
    """Generate normalized embeddings for text chunks."""

    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    if not chunks:
        raise ValueError("Cannot generate embeddings for empty chunks")

    if any(not chunk.text.strip() for chunk in chunks):
        raise ValueError("Chunks must not contain empty text")

    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(
        [chunk.text for chunk in chunks],
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    embeddings = np.asarray(embeddings, dtype=np.float32)

    expected_shape = (len(chunks), EXPECTED_DIMENSIONS)

    if embeddings.shape != expected_shape:
        raise ValueError(
            f"Expected embeddings shape {expected_shape}, "
            f"received {embeddings.shape}"
        )

    if not np.isfinite(embeddings).all():
        raise ValueError("Embeddings contain NaN or infinite values")

    return EmbeddedChunks(
        chunks=chunks,
        embeddings=embeddings,
    )
