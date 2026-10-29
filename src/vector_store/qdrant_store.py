from pathlib import Path
from typing import Any
import logging
import uuid

import numpy as np
from qdrant_client import QdrantClient, models

from src.vector_store.qdrant_filters import (
    build_payload_filter,
    validate_access_metadata,
)

MODEL_DIMENSIONS = 384
COLLECTION_NAME = "airline_hr_policy"

# Stable namespace for deterministic Qdrant point IDs.
POINT_ID_NAMESPACE = uuid.NAMESPACE_URL


class QdrantStore:
    """Persistent vector storage for the Airline HR Policy RAG."""

    logger = logging.getLogger(__name__)

    def __init__(self, persist_directory: Path) -> None:
        """Initialize local persistent storage and ensure the collection exists."""

        persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = QdrantClient(path=str(persist_directory.resolve()))

        try:
            self._ensure_collection()
        except Exception:
            self.client.close()
            raise

    @staticmethod
    def _point_id(chunk_id: str) -> str:
        """Convert an arbitrary chunk ID into a deterministic UUID."""

        return str(
            uuid.uuid5(
                POINT_ID_NAMESPACE,
                f"airline-hr-policy:{chunk_id}",
            )
        )

    def _ensure_collection(self) -> None:
        """Create the collection if missing; validate its vector configuration."""

        if self.client.collection_exists(COLLECTION_NAME):
            collection_info = self.client.get_collection(
                collection_name=COLLECTION_NAME
            )

            vector_config = collection_info.config.params.vectors

            # This implementation supports one unnamed dense vector.
            if isinstance(vector_config, dict):
                raise ValueError(
                    f"Collection '{COLLECTION_NAME}' uses named vectors. "
                    "This store expects a single unnamed dense vector."
                )

            if vector_config.size != MODEL_DIMENSIONS:
                raise ValueError(
                    f"Collection '{COLLECTION_NAME}' expects "
                    f"{vector_config.size} dimensions, but this store "
                    f"requires {MODEL_DIMENSIONS}."
                )

            if vector_config.distance != models.Distance.COSINE:
                raise ValueError(
                    f"Collection '{COLLECTION_NAME}' must use cosine distance."
                )

            self.logger.info(
                "Using existing Qdrant collection: %s",
                COLLECTION_NAME,
            )
            self._ensure_payload_indexes()
            return

        self.client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=MODEL_DIMENSIONS,
                distance=models.Distance.COSINE,
            ),
        )
        self._ensure_payload_indexes()

        self.logger.info(
            "Created Qdrant collection: %s",
            COLLECTION_NAME,
        )

    def _ensure_payload_indexes(self) -> None:
        for field_name, field_schema in [
            ("source", models.PayloadSchemaType.KEYWORD),
            ("allowed_roles", models.PayloadSchemaType.KEYWORD),
            ("document_name", models.PayloadSchemaType.KEYWORD),
            ("start_page", models.PayloadSchemaType.INTEGER),
            ("end_page", models.PayloadSchemaType.INTEGER),
        ]:
            self.client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
            )

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        embeddings: np.ndarray,
        batch_size: int = 100,
    ) -> int:
        """
        Validate and upsert chunks with their precomputed embeddings.

        IMPORTANT:
        This method synchronizes the entire collection against the supplied
        chunks. Pass the complete desired dataset, not just one new PDF's
        chunks, or existing points absent from the input will be deleted.
        """

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        if not chunks:
            raise ValueError(
                "No chunks supplied. Refusing to synchronize an empty dataset."
            )

        vectors = np.asarray(embeddings, dtype=np.float32)

        if vectors.shape != (len(chunks), MODEL_DIMENSIONS):
            raise ValueError(
                f"Expected embedding shape "
                f"({len(chunks)}, {MODEL_DIMENSIONS}), "
                f"received {vectors.shape}."
            )

        if not np.isfinite(vectors).all():
            raise ValueError("Embeddings contain NaN or infinite values.")

        ids = [chunk.get("chunk_id") for chunk in chunks]

        if any(
            not isinstance(chunk_id, str) or not chunk_id.strip() for chunk_id in ids
        ):
            raise ValueError("Every chunk must have a non-empty string chunk_id.")

        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate chunk IDs found in input.")

        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            text = chunk.get("text")
            document_name = chunk.get("document_name")
            start_page = chunk.get("start_page")
            end_page = chunk.get("end_page")
            chunk_index = chunk.get("chunk_index")

            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Chunk {chunk_id} has empty or invalid text.")

            if not isinstance(document_name, str) or not document_name.strip():
                raise ValueError(f"Chunk {chunk_id} has no valid document name.")

            if (
                not isinstance(start_page, int)
                or isinstance(start_page, bool)
                or not isinstance(end_page, int)
                or isinstance(end_page, bool)
                or start_page < 1
                or end_page < start_page
            ):
                raise ValueError(f"Chunk {chunk_id} has an invalid page range.")

            if (
                not isinstance(chunk_index, int)
                or isinstance(chunk_index, bool)
                or chunk_index < 0
            ):
                raise ValueError(f"Chunk {chunk_id} has an invalid chunk index.")

            validate_access_metadata(chunk)

        # Read existing points and map their original chunk IDs to Qdrant IDs.
        # Pagination is necessary because the collection may exceed one batch.
        existing_points: dict[str, Any] = {}
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            for point in points:
                payload = point.payload or {}
                original_id = payload.get("chunk_id")

                if isinstance(original_id, str) and original_id:
                    existing_points[original_id] = point.id
                else:
                    # Legacy or malformed point: it cannot be matched to
                    # an incoming original ID, so mark it for cleanup.
                    existing_points[f"__legacy__:{point.id}"] = point.id

            if next_offset is None:
                break

            offset = next_offset

        current_ids = set(ids)

        stale_point_ids = [
            point_id
            for original_id, point_id in existing_points.items()
            if original_id not in current_ids
        ]

        # Upsert first, so a validation or upsert error doesn't delete the
        # existing dataset before new points have been written.
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            batch_vectors = vectors[start : start + batch_size]

            points_to_upsert = [
                models.PointStruct(
                    id=self._point_id(chunk["chunk_id"]),
                    vector=vector.tolist(),
                    payload={
                        "chunk_id": chunk["chunk_id"],
                        "text": chunk["text"],
                        "document_name": chunk["document_name"],
                        "start_page": chunk["start_page"],
                        "end_page": chunk["end_page"],
                        "chunk_index": chunk["chunk_index"],
                        "source": chunk["source"],
                        "allowed_roles": chunk["allowed_roles"],
                    },
                )
                for chunk, vector in zip(batch, batch_vectors)
            ]

            self.client.upsert(
                collection_name=COLLECTION_NAME,
                points=points_to_upsert,
                wait=True,
            )

        # Delete stale points only after all upsert batches succeed.
        if stale_point_ids:
            for start in range(0, len(stale_point_ids), batch_size):
                batch_ids = stale_point_ids[start : start + batch_size]

                self.client.delete(
                    collection_name=COLLECTION_NAME,
                    points_selector=models.PointIdsList(points=batch_ids),
                    wait=True,
                )

        self.logger.info(
            "Upserted chunks: %d; removed stale points: %d",
            len(chunks),
            len(stale_point_ids),
        )

        return len(chunks)

    def count(self) -> int:
        """Return the exact number of points in the collection."""

        result = self.client.count(
            collection_name=COLLECTION_NAME,
            exact=True,
        )

        return result.count

    def query(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        query_filter: models.Filter | None = None,
        *,
        source: str | None = None,
        document_name: str | None = None,
        role: str | None = None,
        min_page: int | None = None,
        max_page: int | None = None,
    ) -> dict[str, Any]:
        """
        Retrieve the nearest chunks using cosine similarity.

        Returns a ChromaDB-compatible nested result structure.
        The 'distances' values are 1 - Qdrant cosine similarity scores.
        Pass role to include only matching and public chunks. Omitting role
        leaves access filtering disabled.
        """

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        vector = np.asarray(
            query_embedding,
            dtype=np.float32,
        )

        if vector.shape != (MODEL_DIMENSIONS,):
            raise ValueError(
                f"Expected a query vector with {MODEL_DIMENSIONS} "
                f"dimensions, received {vector.shape}."
            )

        if not np.isfinite(vector).all():
            raise ValueError("Query embedding contains invalid values.")

        if np.linalg.norm(vector) == 0:
            raise ValueError("Query embedding cannot be a zero vector.")

        effective_filter = build_payload_filter(
            query_filter,
            source=source,
            document_name=document_name,
            role=role,
            min_page=min_page,
            max_page=max_page,
        )

        if self.count() == 0:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=vector.tolist(),
            limit=min(top_k, self.count()),
            with_payload=True,
            with_vectors=False,
            query_filter=effective_filter,
        )

        results = response.points

        return {
            "ids": [
                [
                    str((point.payload or {}).get("chunk_id", point.id))
                    for point in results
                ]
            ],
            "documents": [[(point.payload or {}).get("text", "") for point in results]],
            "metadatas": [
                [
                    {
                        key: value
                        for key, value in (point.payload or {}).items()
                        if key != "text"
                    }
                    for point in results
                ]
            ],
            "distances": [[1.0 - point.score for point in results]],
        }

    def close(self) -> None:
        """Close the Qdrant client and release local storage resources."""

        self.client.close()

    def __enter__(self) -> "QdrantStore":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    def clear(self, batch_size: int = 100) -> int:

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        # Collect point IDs before deleting anything.
        point_ids = []
        offset = None

        while True:
            points, next_offset = self.client.scroll(
                collection_name=COLLECTION_NAME,
                limit=batch_size,
                offset=offset,
                with_payload=False,
                with_vectors=False,
            )

            point_ids.extend(point.id for point in points)

            if next_offset is None:
                break

        offset = next_offset

        # Delete the collected IDs in batches.
        for start in range(0, len(point_ids), batch_size):
            self.client.delete(
                collection_name=COLLECTION_NAME,
                points_selector=models.PointIdsList(
                    points=point_ids[start : start + batch_size]
                ),
                wait=True,
            )

        self.logger.info("Cleared %d points", len(point_ids))

        return len(point_ids)
