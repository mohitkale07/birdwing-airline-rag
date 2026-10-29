import json
import logging
from pathlib import Path

from src.retrieval.search import HybridHRPolicyRetriever

logger = logging.getLogger(__name__)

K_VALUES = (1, 3, 5)


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


def evaluate_case(
    retriever: HybridHRPolicyRetriever,
    case: dict,
    max_k: int,
) -> dict:
    expected_pages = set(case["expected_pages"])
    results = retriever.search(
        case["question"],
        top_k=max_k,
        role=case.get("role", "hr"),
    )

    retrieved_page_ranges = [
        (result["start_page"], result["end_page"]) for result in results
    ]

    metrics = {}

    for k in K_VALUES:
        top_pages = {
            page
            for start_page, end_page in retrieved_page_ranges[:k]
            for page in range(start_page, end_page + 1)
        }
        relevant_found = len(expected_pages & top_pages)

        metrics[f"recall@{k}"] = relevant_found / len(expected_pages)

        metrics[f"hit@{k}"] = int(relevant_found > 0)

    reciprocal_rank = 0.0

    for rank, (start_page, end_page) in enumerate(retrieved_page_ranges, start=1):
        if any(start_page <= page <= end_page for page in expected_pages):
            reciprocal_rank = 1.0 / rank
            break

    return {
        "id": case.get("id", "UNKNOWN"),
        "question": case["question"],
        "expected_pages": sorted(expected_pages),
        "retrieved_page_ranges": retrieved_page_ranges,
        "metrics": metrics,
        "reciprocal_rank": reciprocal_rank,
    }


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]
    dataset_path = project_root / "data" / "evaluation" / "retrieval_test_cases.json"

    test_cases = load_test_cases(dataset_path)
    retriever = HybridHRPolicyRetriever(project_root)

    reports = []

    for case in test_cases:
        report = evaluate_case(
            retriever,
            case,
            max_k=max(K_VALUES),
        )
        reports.append(report)

        metrics = report["metrics"]

        print(f"\n{'=' * 70}")
        print(f"{report['id']}: {report['question']}")
        print(f"Expected pages: {report['expected_pages']}")
        print(f"Retrieved page ranges: {report['retrieved_page_ranges']}")
        print(
            f"Recall@1={metrics['recall@1']:.2f} | "
            f"Recall@3={metrics['recall@3']:.2f} | "
            f"Recall@5={metrics['recall@5']:.2f}"
        )

    print(f"\n{'=' * 70}")
    print("OVERALL RETRIEVAL EVALUATION")
    print(f"Test cases: {len(reports)}")

    for k in K_VALUES:
        average_recall = sum(
            report["metrics"][f"recall@{k}"] for report in reports
        ) / len(reports)

        hit_rate = sum(report["metrics"][f"hit@{k}"] for report in reports) / len(
            reports
        )

        print(f"Recall@{k}: {average_recall:.3f} | " f"Hit rate@{k}: {hit_rate:.3f}")

    mrr = sum(report["reciprocal_rank"] for report in reports) / len(reports)

    print(f"MRR: {mrr:.3f}")

    report_path = (
        project_root / "data" / "evaluation" / "retrieval_evaluation_report.json"
    )

    with report_path.open("w", encoding="utf-8") as file:
        json.dump(reports, file, ensure_ascii=False, indent=2)

    print(f"Detailed report saved to: {report_path}")


if __name__ == "__main__":
    main()
