import json
import logging
from pathlib import Path

import numpy as np
from src.vector_store.qdrant_store import QdrantStore

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]
    processed_dir = project_root / "data" / "processed"

    chunks_path = processed_dir / "chunks.json"
    embeddings_path = processed_dir / "embeddings.npy"
    persist_directory = project_root / "data" / "qdrant"

    if not chunks_path.is_file():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

    if not embeddings_path.is_file():
        raise FileNotFoundError(f"Embeddings file not found: {embeddings_path}")

    with chunks_path.open("r", encoding="utf-8") as file:
        chunks = json.load(file)

    embeddings = np.load(
        embeddings_path,
        allow_pickle=False,
    )

    with QdrantStore(persist_directory) as store:
        inserted_or_updated = store.upsert_chunks(
            chunks,
            embeddings,
        )

        logger.info("Chunks processed: %d", inserted_or_updated)
        logger.info("Records currently stored: %d", store.count())
        logger.info("Qdrant location: %s", persist_directory)


if __name__ == "__main__":
    main()
