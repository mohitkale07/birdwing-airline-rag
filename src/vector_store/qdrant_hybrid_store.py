from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

import numpy as np
from qdrant_client import QdrantClient, models

from src.vector_store.qdrant_filters import (
    build_payload_filter,
    validate_access_metadata,
)


class QdrantHybridStore:
    """Qdrant store supporting dense + sparse hybrid retrieval."""

    COLLECTION_NAME = "airline_hr_policy_hybrid"

    def __init__(self, persist_directory: Path) -> None:
        persist_directory.mkdir(parents=True, exist_ok=True)

        self.client = QdrantClient(path=str(persist_directory.resolve()))

    def recreate_collection(self, dense_dimension: int) -> None:
        """Recreate only the hybrid collection."""

        if self.client.collection_exists(self.COLLECTION_NAME):
            self.client.delete_collection(self.COLLECTION_NAME)

        self.client.create_collection(
            collection_name=self.COLLECTION_NAME,
            vectors_config={
                "dense": models.VectorParams(
                    size=dense_dimension,
                    distance=models.Distance.COSINE,
                )
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF,
                )
            },
        )

        # Index payload fields used by metadata filters.
        for field_name, field_schema in [
            ("document_name", models.PayloadSchemaType.KEYWORD),
            ("source", models.PayloadSchemaType.KEYWORD),
            ("allowed_roles", models.PayloadSchemaType.KEYWORD),
            ("start_page", models.PayloadSchemaType.INTEGER),
            ("end_page", models.PayloadSchemaType.INTEGER),
        ]:
            self.client.create_payload_index(
                collection_name=self.COLLECTION_NAME,
                field_name=field_name,
                field_schema=field_schema,
            )

    def upsert_chunks(
        self,
        chunks: list[dict[str, Any]],
        dense_embeddings,
        sparse_embeddings,
        batch_size: int = 100,
    ) -> None:
        """Store both vector representations with each chunk."""

        if batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")

        if not (len(chunks) == len(dense_embeddings) == len(sparse_embeddings)):
            raise ValueError(
                "Chunks, dense embeddings and sparse embeddings "
                "must have the same length."
            )

        if not chunks:
            raise ValueError("No chunks supplied for ingestion")

        dense_vectors = np.asarray(dense_embeddings, dtype=np.float32)
        if dense_vectors.ndim != 2 or not np.isfinite(dense_vectors).all():
            raise ValueError("Dense embeddings must be a finite 2D array")

        if len(dense_vectors) != len(chunks):
            raise ValueError("Dense embedding count does not match chunks")

        for chunk in chunks:
            if not isinstance(chunk.get("text"), str) or not chunk["text"].strip():
                raise ValueError(f"Chunk {chunk.get('chunk_id')} has empty text")
            validate_access_metadata(chunk)

        for start in range(0, len(chunks), batch_size):
            batch_chunks = chunks[start : start + batch_size]
            batch_dense = dense_vectors[start : start + batch_size]
            batch_sparse = sparse_embeddings[start : start + batch_size]

            points = []

            for chunk, dense, sparse in zip(batch_chunks, batch_dense, batch_sparse):
                chunk_id = str(
                    chunk.get(
                        "chunk_id",
                        f"{chunk.get('document_name', 'document')}:"
                        f"{chunk.get('chunk_index', start)}:"
                        f"{chunk.get('start_page', 0)}",
                    )
                )

                point_id = str(uuid5(NAMESPACE_URL, f"airline-hr:{chunk_id}"))

                payload = {
                    **chunk,
                    "chunk_id": chunk_id,
                    "text": chunk["text"],
                }

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector={
                            "dense": dense.tolist(),
                            "sparse": models.SparseVector(
                                indices=sparse.indices.tolist(),
                                values=sparse.values.tolist(),
                            ),
                        },
                        payload=payload,
                    )
                )

            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=points,
                wait=True,
            )

    def hybrid_search(
        self,
        dense_query,
        sparse_query,
        top_k: int = 5,
        query_filter: models.Filter | None = None,
        prefetch_limit: int = 20,
        *,
        source: str | None = None,
        document_name: str | None = None,
        role: str | None = None,
        min_page: int | None = None,
        max_page: int | None = None,
    ) -> list[dict[str, Any]]:
        """Fuse dense and sparse results using RRF.

        Pass role to include only matching and public chunks. Omitting role
        leaves access filtering disabled.
        """

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")
        if prefetch_limit <= 0:
            raise ValueError("prefetch_limit must be greater than zero")

        effective_filter = build_payload_filter(
            query_filter,
            source=source,
            document_name=document_name,
            role=role,
            min_page=min_page,
            max_page=max_page,
        )

        response = self.client.query_points(
            collection_name=self.COLLECTION_NAME,
            prefetch=[
                models.Prefetch(
                    query=dense_query.tolist(),
                    using="dense",
                    limit=max(prefetch_limit, top_k),
                    filter=effective_filter,
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_query.indices.tolist(),
                        values=sparse_query.values.tolist(),
                    ),
                    using="sparse",
                    limit=max(prefetch_limit, top_k),
                    filter=effective_filter,
                ),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
            with_payload=True,
        )

        results = []

        for point in response.points:
            payload = point.payload or {}

            results.append(
                {
                    "chunk_id": payload.get("chunk_id"),
                    "text": payload.get("text", ""),
                    "document_name": payload.get("document_name"),
                    "start_page": payload.get("start_page"),
                    "end_page": payload.get("end_page"),
                    "source": payload.get("source"),
                    "allowed_roles": payload.get("allowed_roles"),
                    "score": point.score,
                }
            )

        return results

    def count(self) -> int:
        result = self.client.count(
            collection_name=self.COLLECTION_NAME,
            exact=True,
        )
        return result.count

    def close(self) -> None:
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
