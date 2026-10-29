import argparse
import json
import logging
from pathlib import Path
from typing import Any

from openai import OpenAIError

from src.generation.answer_question import (
    _answer_from_candidates,
    retrieve_candidates,
)
from src.retrieval.search import USER_ROLES

logger = logging.getLogger(__name__)

REVIEW_FIELDS = (
    "correctness",
    "completeness",
    "citation_accuracy",
    "abstention_correct",
    "access_control_pass",
)
REVIEW_CRITERIA = {
    "correctness": "Facts are accurate and supported by the cited source.",
    "completeness": "The answer covers all required_facts without omitting key conditions.",
    "citation_accuracy": "Citations identify the expected document and supporting pages.",
    "abstention_correct": "The answer abstains exactly when should_abstain is true.",
    "access_control_pass": "No restricted document content is retrieved or cited.",
}


def load_test_cases(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Answer-quality dataset not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        cases = json.load(file)

    if not isinstance(cases, list) or not cases:
        raise ValueError("Answer-quality dataset must be a non-empty list")

    seen_ids: set[str] = set()
    for case in cases:
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id.strip() or case_id in seen_ids:
            raise ValueError(f"Missing or duplicate test case id: {case_id!r}")
        seen_ids.add(case_id)

        if not isinstance(case.get("question"), str) or not case["question"].strip():
            raise ValueError(f"Missing question in test case {case_id}")

        if case.get("role") not in USER_ROLES:
            raise ValueError(f"Invalid role in test case {case_id}")

        if not isinstance(case.get("expected_sources"), list):
            raise ValueError(f"Invalid expected_sources in test case {case_id}")

        if not isinstance(case.get("required_facts"), list):
            raise ValueError(f"Invalid required_facts in test case {case_id}")

        if not isinstance(case.get("should_abstain"), bool):
            raise ValueError(f"Invalid should_abstain in test case {case_id}")

    return cases


def save_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)


def _empty_review() -> dict[str, int | None | str]:
    review: dict[str, int | None | str] = {
        field: None for field in REVIEW_FIELDS
    }
    review["notes"] = ""
    return review


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate answers for the golden dataset for manual quality review."
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Run only the first N cases (useful for a small initial/API-limited run).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the report to this path instead of the default baseline path.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing report at the selected output path.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Run only this case ID; may be supplied more than once.",
    )
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="Inspect retrieved chunks and access control without calling the LLM.",
    )
    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be greater than zero")

    project_root = Path(__file__).resolve().parents[2]
    dataset_path = project_root / "data" / "evaluation" / "answer_quality_test_cases.json"
    report_path = args.output or (
        project_root / "data" / "evaluation" / "answer_quality_baseline.json"
    )
    if not report_path.is_absolute():
        report_path = project_root / report_path
    if report_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Report already exists: {report_path}. Use --output for a new report "
            "or --overwrite to replace it."
        )

    test_cases = load_test_cases(dataset_path)

    if args.case_ids:
        cases_by_id = {case["id"]: case for case in test_cases}
        missing_case_ids = sorted(set(args.case_ids) - cases_by_id.keys())
        if missing_case_ids:
            raise ValueError(
                "Unknown evaluation case ID(s): " + ", ".join(missing_case_ids)
            )
        test_cases = [cases_by_id[case_id] for case_id in dict.fromkeys(args.case_ids)]

    if args.limit is not None:
        test_cases = test_cases[: args.limit]

    report: dict[str, Any] = {
        "case_count": len(test_cases),
        "review_scale": "Score applicable numeric fields from 0 (failed) to 2 (good).",
        "review_criteria": REVIEW_CRITERIA,
        "cases": [],
    }
    save_report(report_path, report)

    for case in test_cases:
        result: dict[str, Any] = {
            **case,
            "status": "running",
            "answer": None,
            "error": None,
            "retrieved_chunks": [],
            "retrieval_validation": None,
            "review": _empty_review(),
        }
        report["cases"].append(result)
        save_report(report_path, report)

        try:
            candidates = retrieve_candidates(
                case["question"],
                role=case["role"],
            )
            result["retrieved_chunks"] = [
                {
                    "chunk_id": candidate.get("chunk_id"),
                    "document_name": candidate.get("document_name"),
                    "source": candidate.get("source"),
                    "start_page": candidate.get("start_page"),
                    "end_page": candidate.get("end_page"),
                }
                for candidate in candidates
            ]

            expected_documents = {
                source["document_name"] for source in case["expected_sources"]
            }
            retrieved_documents = {
                candidate.get("document_name") for candidate in candidates
            }
            restricted_documents = set(case.get("restricted_sources", []))
            found_restricted = sorted(retrieved_documents & restricted_documents)
            result["retrieval_validation"] = {
                "expected_documents_found": sorted(
                    expected_documents & retrieved_documents
                ),
                "restricted_documents_found": found_restricted,
            }
            if case["test_type"] == "access_control":
                result["review"]["access_control_pass"] = (
                    0 if found_restricted else 2
                )
                if found_restricted:
                    result["review"]["notes"] = (
                        "Restricted documents were returned by retrieval: "
                        + ", ".join(found_restricted)
                    )

            if args.retrieval_only:
                result["status"] = "retrieval_only"
                save_report(report_path, report)
                print(
                    f"Retrieved {len(candidates)} chunks for {case['id']} "
                    f"({case['role']})"
                )
                continue

            result["answer"] = _answer_from_candidates(case["question"], candidates)
            result["status"] = "completed"
        except OpenAIError as exc:
            result["status"] = "error"
            result["error"] = f"{type(exc).__name__}: {exc}"
            save_report(report_path, report)
            logger.exception(
                "LLM provider failed for evaluation case %s; saved partial report",
                case["id"],
            )
            raise

        save_report(report_path, report)
        print(f"Completed {case['id']} ({case['role']})")

    print(f"Answer-quality baseline saved to: {report_path}")
    print("Review each answer and fill in its review scores and notes.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    main()
