import logging
from pathlib import Path

from src.retrieval.search import HybridHRPolicyRetriever


def main() -> None:
    logging.basicConfig(level=logging.WARNING)

    project_root = Path(__file__).resolve().parents[2]
    retriever = HybridHRPolicyRetriever(project_root)

    questions = [
        {
            "id": "Q05",
            "question": (
                "What disciplinary or corrective steps can be taken "
                "when an employee violates probation requirements?"
            ),
        },
        {
            "id": "Q06",
            "question": (
                "What is the maximum duration of a performance-related "
                "employment extension beyond the original probation period?"
            ),
        },
    ]

    for item in questions:
        print("\n" + "=" * 80)
        print(f"{item['id']}: {item['question']}")

        results = retriever.search(item["question"], top_k=5, role="hr")

        for rank, result in enumerate(results, start=1):
            print("\n" + "-" * 80)
            print(f"Rank: {rank}")
            print(f"Pages: {result['start_page']}-{result['end_page']}")
            print(f"Chunk ID: {result['chunk_id']}")
            print(f"Hybrid score: {result['score']:.4f}")
            print(f"Text:\n{result['text']}")


if __name__ == "__main__":
    main()
