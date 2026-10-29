import logging
from pathlib import Path

from src.retrieval.search import HybridHRPolicyRetriever
from src.retrieval.reranker import HRPolicyReranker


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    project_root = Path(__file__).resolve().parents[2]

    retriever = HybridHRPolicyRetriever(project_root)
    reranker = HRPolicyReranker()

    question = (
        "By when must the exit interview be scheduled "
        "after the employee's last working day?"
    )

    # Retrieve a larger candidate set before reranking.
    candidates = retriever.search(question, top_k=10, role="hr")

    print("\n--- Original embedding ranking ---")

    for rank, result in enumerate(candidates[:5], start=1):
        print(
            f"{rank}. {result['chunk_id'][:12]} | "
            f"pages {result['start_page']}-{result['end_page']} | "
            f"hybrid score {result['score']:.4f}"
        )

    reranked = reranker.rerank(
        question=question,
        candidates=candidates,
        top_k=5,
    )

    print("\n--- Cross-encoder reranking ---")

    for rank, result in enumerate(reranked, start=1):
        print(
            f"{rank}. {result['chunk_id'][:12]} | "
            f"pages {result['start_page']}-{result['end_page']} | "
            f"rerank score {result['rerank_score']:.4f}"
        )
        print(result["text"][:500])
        print()

    target_chunk_id = (
        "86a159f9634d2221ad282d55fe98f2642b41b4b7ea10af39" "b68425031405ff71"
    )

    target_rank = next(
        (
            rank
            for rank, result in enumerate(reranked, start=1)
            if result["chunk_id"] == target_chunk_id
        ),
        None,
    )

    print(
        "Target exit-interview chunk rank:",
        target_rank if target_rank is not None else "Not in reranked top 5",
    )


if __name__ == "__main__":
    main()
