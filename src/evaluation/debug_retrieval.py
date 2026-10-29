import logging
from pathlib import Path

from src.retrieval.search import HybridHRPolicyRetriever


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    project_root = Path(__file__).resolve().parents[2]
    retriever = HybridHRPolicyRetriever(project_root)

    question = (
        "By when must the exit interview be scheduled "
        "after the employee's last working day?"
    )

    results = retriever.search(question, top_k=10, role="hr")

    print(f"\nQuestion: {question}")
    print(f"Retrieved chunks: {len(results)}")

    for rank, result in enumerate(results, start=1):
        print("\n" + "=" * 70)
        print(f"Rank: {rank}")
        print(f"Chunk ID: {result['chunk_id']}")
        print(f"Document: {result['document_name']}")
        print(f"Pages: {result['start_page']}" f"–{result['end_page']}")
        print(f"Hybrid score: {result['score']:.4f}")
        print("\nRetrieved text:")
        print(result["text"])


if __name__ == "__main__":
    main()
