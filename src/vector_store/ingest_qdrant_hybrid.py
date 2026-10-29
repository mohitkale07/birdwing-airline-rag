import json
from pathlib import Path

import numpy as np
from fastembed import SparseTextEmbedding

from src.vector_store.qdrant_hybrid_store import QdrantHybridStore

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CHUNKS_PATH = PROJECT_ROOT / "data" / "processed" / "chunks.json"
DENSE_EMBEDDINGS_PATH = PROJECT_ROOT / "data" / "processed" / "embeddings.npy"
QDRANT_PATH = PROJECT_ROOT / "data" / "qdrant_hybrid"

SPARSE_MODEL_NAME = "Qdrant/bm25"


def main() -> None:
    # Load the existing chunk dataset.
    with CHUNKS_PATH.open("r", encoding="utf-8") as file:
        chunks = json.load(file)

    # Support either a JSON list or {"chunks": [...]}.
    if isinstance(chunks, dict):
        chunks = chunks["chunks"]

    if not chunks:
        raise ValueError("No chunks found in chunks.json")

    dense_embeddings = np.load(DENSE_EMBEDDINGS_PATH)

    if len(chunks) != len(dense_embeddings):
        raise ValueError(
            f"Chunk count ({len(chunks)}) does not match "
            f"dense embedding count ({len(dense_embeddings)})."
        )

    texts = [chunk["text"] for chunk in chunks]

    print(f"Loaded {len(chunks)} chunks.")
    print("Generating sparse embeddings...")

    sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)

    sparse_embeddings = list(sparse_model.embed(texts))

    if len(sparse_embeddings) != len(chunks):
        raise ValueError("Sparse embedding count does not match chunks.")

    print("Creating hybrid collection and ingesting points...")

    with QdrantHybridStore(QDRANT_PATH) as store:
        store.recreate_collection(dense_dimension=dense_embeddings.shape[1])

        store.upsert_chunks(
            chunks=chunks,
            dense_embeddings=dense_embeddings,
            sparse_embeddings=sparse_embeddings,
        )

        print(f"Ingested points: {store.count()}")
        print(f"Collection: {store.COLLECTION_NAME}")
        print(f"Storage path: {QDRANT_PATH}")

    print("Hybrid ingestion completed.")


if __name__ == "__main__":
    main()
