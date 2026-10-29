from pathlib import Path
from typing import Any

from fastembed import SparseTextEmbedding
from qdrant_client import models
from sentence_transformers import SentenceTransformer

from src.retrieval.search import USER_ROLES
from src.vector_store.qdrant_hybrid_store import QdrantHybridStore

DENSE_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL_NAME = "Qdrant/bm25"


class HybridHRPolicyRetriever:
    def __init__(self, project_root: Path) -> None:
        self.dense_model = SentenceTransformer(DENSE_MODEL_NAME)

        self.sparse_model = SparseTextEmbedding(model_name=SPARSE_MODEL_NAME)

        self.store = QdrantHybridStore(project_root / "data" / "qdrant_hybrid")

    def search(
        self,
        question: str,
        top_k: int = 5,
        document_name: str | None = None,
        source: str | None = None,
        min_page: int | None = None,
        max_page: int | None = None,
        role: str = "public",
    ) -> list[dict[str, Any]]:
        question = question.strip()

        if not question:
            raise ValueError("Search question cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        role = role.strip().casefold()
        if role not in USER_ROLES:
            raise ValueError(
                f"Unsupported role {role!r}. Expected one of: "
                + ", ".join(sorted(USER_ROLES))
            )

        if min_page is not None and min_page < 1:
            raise ValueError("min_page must be at least 1")

        if max_page is not None and max_page < 1:
            raise ValueError("max_page must be at least 1")

        if min_page is not None and max_page is not None and min_page > max_page:
            raise ValueError("min_page cannot exceed max_page")

        conditions = []

        if document_name is not None:
            if not document_name.strip():
                raise ValueError("document_name cannot be empty")

            conditions.append(
                models.FieldCondition(
                    key="document_name",
                    match=models.MatchValue(value=document_name),
                )
            )

        # Match chunks that overlap the requested page range.
        if min_page is not None:
            conditions.append(
                models.FieldCondition(
                    key="end_page",
                    range=models.Range(gte=min_page),
                )
            )

        if max_page is not None:
            conditions.append(
                models.FieldCondition(
                    key="start_page",
                    range=models.Range(lte=max_page),
                )
            )

        query_filter = models.Filter(must=conditions) if conditions else None

        dense_query = self.dense_model.encode(
            question,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )

        sparse_query = next(iter(self.sparse_model.query_embed([question])))

        return self.store.hybrid_search(
            dense_query=dense_query,
            sparse_query=sparse_query,
            top_k=top_k,
            query_filter=query_filter,
            source=source,
            role=role,
        )

    def close(self) -> None:
        self.store.close()
