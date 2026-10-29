import logging
from pathlib import Path
from typing import Any

from sentence_transformers import SentenceTransformer
from qdrant_client import models
from fastembed import SparseTextEmbedding

from src.retrieval.reranker import HRPolicyReranker
from src.vector_store.qdrant_hybrid_store import QdrantHybridStore

DENSE_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
SPARSE_MODEL_NAME = "Qdrant/bm25"
USER_ROLES = frozenset(
    {"hr", "admin", "employee", "customer", "support_agent", "public"}
)

logger = logging.getLogger(__name__)

SEARCH_CANDIDATE_K = 20
SEARCH_TOP_K = 5


class HybridHRPolicyRetriever:
    """Retrieve HR policy passages using dense-only or hybrid search."""

    def __init__(self, project_root: Path) -> None:
        # =====================================================
        # ORIGINAL: DENSE-ONLY RETRIEVER
        # Uncomment this section to use dense-only retrieval.
        # =====================================================
        # self.model = SentenceTransformer(DENSE_MODEL_NAME)
        # self.store = QdrantStore(
        #     project_root / "data" / "qdrant"
        # )

        # =====================================================
        # NEW: HYBRID RETRIEVER (ACTIVE)
        # =====================================================
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

        # Build metadata conditions.
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

        # Match chunks overlapping the requested page range.
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


def main() -> None:
    logging.basicConfig(level=logging.INFO)

    project_root = Path(__file__).resolve().parents[2]
    retriever = HybridHRPolicyRetriever(project_root)

    try:
        print("Available roles: hr, admin, employee, customer, support_agent, public")
        role = input("Search as role [public]: ").strip() or "public"
        question = input("Ask an HR policy question: ").strip()

        candidates = retriever.search(
            question,
            top_k=SEARCH_CANDIDATE_K,
            role=role,
        )
        results = HRPolicyReranker().rerank(
            question,
            candidates,
            top_k=SEARCH_TOP_K,
        )

        # Example 2: Filter by document.
        # results = retriever.search(
        #     question,
        #     top_k=3,
        #     document_name="airline_hr_policy.pdf",
        # )

        # Example 3: Filter by page range.
        # results = retriever.search(
        #     question,
        #     top_k=3,
        #     min_page=5,
        #     max_page=10,
        # )

        # Example 4: Combine document and page filters.
        # results = retriever.search(
        #     question,
        #     top_k=3,
        #     document_name="airline_hr_policy.pdf",
        #     min_page=5,
        #     max_page=10,
        # )

        if not results:
            print("No matching chunks found. Check your filters and ingestion.")
            return

        for rank, result in enumerate(results, start=1):
            print(f"\n{'=' * 60}")
            print(f"Result {rank}")
            print(f"Chunk ID: {result['chunk_id']}")
            print(f"Source: {result['document_name']}")

            page_range = str(result["start_page"])
            if result["end_page"] != result["start_page"]:
                page_range += f"–{result['end_page']}"

            print(f"Pages: {page_range}")

            print(f"Reranker score: {result['rerank_score']:.4f}")

            print(f"\n{result['text']}")

    except ValueError as exc:
        print(f"Invalid query: {exc}")

    finally:
        retriever.close()


if __name__ == "__main__":
    main()
