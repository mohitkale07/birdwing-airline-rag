import json
import logging
from pathlib import Path

from src.retrieval.search import HybridHRPolicyRetriever
from src.retrieval.reranker import HRPolicyReranker

logger = logging.getLogger(__name__)

K_VALUES = (1, 3, 5)
CANDIDATE_K = 10


def load_test_cases(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        test_cases = json.load(file)

    if not isinstance(test_cases, list) or not test_cases:
        raise ValueError("Evaluation dataset must be a non-empty list")

    for case in test_cases:
        if not case.get("question", "").strip():
            raise ValueError(f"Missing question in test case: {case}")

        pages = case.get("expected_pages")

        if (
            not isinstance(pages, list)
            or not pages
            or any(type(page) is not int or page <= 0 for page in pages)
        ):
            raise ValueError(f"Invalid expected_pages in test case: {case.get('id')}")

    return test_cases


def evaluate_results(
    case: dict,
    results: list[dict],
) -> dict:
    expected_pages = set(case["expected_pages"])

    page_ranges = [(result["start_page"], result["end_page"]) for result in results]

    metrics = {}

    for k in K_VALUES:
        top_pages = {
            page
            for start_page, end_page in page_ranges[:k]
            for page in range(start_page, end_page + 1)
        }

        relevant_found = len(expected_pages & top_pages)

        metrics[f"recall@{k}"] = relevant_found / len(expected_pages)
        metrics[f"hit@{k}"] = int(relevant_found > 0)

    reciprocal_rank = 0.0

    for rank, (start_page, end_page) in enumerate(page_ranges, start=1):
        if any(start_page <= page <= end_page for page in expected_pages):
            reciprocal_rank = 1.0 / rank
            break

    return {
        "id": case.get("id", "UNKNOWN"),
        "question": case["question"],
        "expected_pages": sorted(expected_pages),
        "retrieved_page_ranges": [list(page_range) for page_range in page_ranges],
        "retrieved_chunk_ids": [result["chunk_id"] for result in results],
        "metrics": metrics,
        "reciprocal_rank": reciprocal_rank,
    }


def print_summary(
    title: str,
    reports: list[dict],
) -> None:
    print(f"\n{'=' * 70}")
    print(title)
    print(f"Test cases: {len(reports)}")

    for k in K_VALUES:
        recall = sum(report["metrics"][f"recall@{k}"] for report in reports) / len(
            reports
        )

        hit_rate = sum(report["metrics"][f"hit@{k}"] for report in reports) / len(
            reports
        )

        print(f"Recall@{k}: {recall:.3f} | " f"Hit rate@{k}: {hit_rate:.3f}")

    mrr = sum(report["reciprocal_rank"] for report in reports) / len(reports)

    print(f"MRR: {mrr:.3f}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]

    dataset_path = project_root / "data" / "evaluation" / "retrieval_test_cases.json"

    test_cases = load_test_cases(dataset_path)

    retriever = HybridHRPolicyRetriever(project_root)
    reranker = HRPolicyReranker()

    baseline_reports = []
    reranked_reports = []

    for case in test_cases:
        # Retrieve once so both rankings use the same candidates.
        candidates = retriever.search(
            case["question"],
            top_k=CANDIDATE_K,
            role=case.get("role", "hr"),
        )

        baseline = evaluate_results(case, candidates)

        reranked_candidates = reranker.rerank(
            question=case["question"],
            candidates=candidates,
            top_k=CANDIDATE_K,
        )

        reranked = evaluate_results(
            case,
            reranked_candidates,
        )

        baseline_reports.append(baseline)
        reranked_reports.append(reranked)

        print(f"\n{'-' * 70}")
        print(f"{case.get('id', 'UNKNOWN')}: {case['question']}")
        print(f"Baseline MRR contribution: " f"{baseline['reciprocal_rank']:.3f}")
        print(f"Reranked MRR contribution: " f"{reranked['reciprocal_rank']:.3f}")

    print_summary(
        "BASELINE: EMBEDDING RETRIEVAL",
        baseline_reports,
    )

    print_summary(
        "RERANKED: EMBEDDING RETRIEVAL + CROSS-ENCODER",
        reranked_reports,
    )

    output = {
        "candidate_k": CANDIDATE_K,
        "baseline": baseline_reports,
        "reranked": reranked_reports,
    }

    report_path = (
        project_root / "data" / "evaluation" / "reranked_evaluation_report.json"
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, ensure_ascii=False, indent=2)

    print(f"\nDetailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
