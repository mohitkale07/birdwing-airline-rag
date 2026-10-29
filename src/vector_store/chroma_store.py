from pathlib import Path
from typing import Any
import logging
import chromadb
import numpy as np

MODEL_DIMENSIONS = 384
COLLECTION_NAME = "airline_hr_policy"


class ChromaStore:
    """Persistent vector storage for the Airline HR Policy RAG."""

    logger = logging.getLogger(__name__)
    def __init__(self, persist_directory: Path) -> None:
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_directory.resolve()))

        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={
                "hnsw:space": "cosine",
                "description": "Airline HR Policy document chunks",
            },
        )

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: np.ndarray,
        batch_size: int = 100,
    ) -> int:
        """Validate and persist chunks with their precomputed vectors."""

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        vectors = np.asarray(embeddings, dtype=np.float32)

        if len(chunks) == 0:
            raise ValueError("No chunks supplied for ingestion")

        if vectors.shape != (len(chunks), MODEL_DIMENSIONS):
            raise ValueError(
                f"Expected embedding shape "
                f"({len(chunks)}, {MODEL_DIMENSIONS}), "
                f"received {vectors.shape}"
            )

        if not np.isfinite(vectors).all():
            raise ValueError("Embeddings contain NaN or infinite values")

        ids = [chunk["chunk_id"] for chunk in chunks]

        if any(not isinstance(item, str) or not item for item in ids):
            raise ValueError("Every chunk must have a non-empty chunk_id")

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate chunk IDs found in input")

        for chunk in chunks:
            if not chunk.get("text", "").strip():
                raise ValueError(f"Chunk {chunk.get('chunk_id')} has empty text")

            if not chunk.get("document_name"):
                raise ValueError(f"Chunk {chunk.get('chunk_id')} has no document name")

            if (
                not isinstance(chunk.get("start_page"), int)
                or not isinstance(chunk.get("end_page"), int)
                or chunk["start_page"] > chunk["end_page"]
            ):
                raise ValueError(
                    f"Chunk {chunk.get('chunk_id')} has invalid page range"
                )
            if not isinstance(chunk.get("chunk_index"), int):
                raise ValueError(f"Chunk {chunk.get('chunk_id')} has invalid chunk index")

        # Remove stale records that are no longer present in the input.
        existing = self.collection.get(include=["metadatas"])
        existing_ids = set(existing["ids"])
        current_ids = set(ids)

        stale_ids = existing_ids - current_ids

        if stale_ids:
            stale_ids = list(stale_ids)

            for start in range(0, len(stale_ids), batch_size):
                self.collection.delete(ids=stale_ids[start : start + batch_size])

        self.logger.info("Removed stale chunks: %d", len(stale_ids))
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            batch_vectors = vectors[start : start + batch_size]

            self.collection.upsert(
                ids=[chunk["chunk_id"] for chunk in batch],
                documents=[chunk["text"] for chunk in batch],
                embeddings=batch_vectors.tolist(),
                metadatas=[
                    {
                        "document_name": chunk["document_name"],
                        "start_page": chunk["start_page"],
                        "end_page": chunk["end_page"],
                        "chunk_index": chunk["chunk_index"],
                    }
                    for chunk in batch
                ],
            )

        return len(chunks)

    def count(self) -> int:
        """Return the number of records in the collection."""
        return self.collection.count()

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """Retrieve the nearest chunks using cosine distance."""

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        vector = np.asarray(query_embedding, dtype=np.float32)

        if vector.shape != (MODEL_DIMENSIONS,):
            raise ValueError(
                f"Expected a query vector with {MODEL_DIMENSIONS} "
                f"dimensions, received {vector.shape}"
            )

        if not np.isfinite(vector).all():
            raise ValueError("Query embedding contains invalid values")

        if np.linalg.norm(vector) == 0:
            raise ValueError("Query embedding cannot be a zero vector")

        if self.count() == 0:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        return self.collection.query(
            query_embeddings=[vector.tolist()],
            n_results=min(top_k, self.count()),
            include=["documents", "metadatas", "distances"],
        )
