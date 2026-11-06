from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.retrieval.search import USER_ROLES, HybridHRPolicyRetriever
from src.retrieval.reranker import HRPolicyReranker
from src.generation.context_builder import format_context
from src.generation.prompt_builder import build_prompt
from src.generation.llm_client import (
    generate_answer,
    generate_search_queries,
)

# Retrieve more candidates, then rerank and select the best passages.
CANDIDATE_K = 20
FINAL_TOP_K = 5
COMPREHENSIVE_CANDIDATE_K = 50
COMPREHENSIVE_TOP_K = 20


def _is_comprehensive_question(question: str) -> bool:
    normalized = question.casefold()
    return any(
        phrase in normalized
        for phrase in (
            "find all",
            "list all",
            "all policy",
            "all requirements",
            "every requirement",
            "comprehensive",
            "including any exceptions",
            "include any exceptions",
        )
    )


def _validate_question_and_role(question: str, role: str) -> tuple[str, str]:
    question = question.strip()
    if not question:
        raise ValueError("Question cannot be empty")

    role = role.strip().casefold()
    if role not in USER_ROLES:
        raise ValueError(
            f"Unsupported role {role!r}. Expected one of: "
            + ", ".join(sorted(USER_ROLES))
        )

    return question, role


def retrieve_candidates(
    question: str,
    role: str = "public",
    *,
    show_query_count: bool = False,
) -> list[dict]:
    """Retrieve role-filtered chunks for a question."""
    question, role = _validate_question_and_role(question, role)
    project_root = Path(__file__).resolve().parents[2]
    comprehensive = _is_comprehensive_question(question)
    candidate_k = COMPREHENSIVE_CANDIDATE_K if comprehensive else CANDIDATE_K

    retriever = HybridHRPolicyRetriever(project_root)
    try:
        query_variants = generate_search_queries(question)
        if show_query_count:
            print(
                f"Generated {len(query_variants)} alternate queries; "
                f"searching with {len(query_variants) + 1} queries total "
                "(including your original question)."
            )
            for index, query in enumerate(query_variants, start=1):
                print(f"  {index}. {query}")

        return retriever.search_multi_query(
            question,
            query_variants,
            top_k=candidate_k,
            role=role,
        )
    finally:
        retriever.close()


@dataclass(frozen=True)
class PreparedAnswer:
    prompt: str | None
    sources: list[dict[str, Any]]


def _rerank_candidates(question: str, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []

    comprehensive = _is_comprehensive_question(question)
    final_top_k = COMPREHENSIVE_TOP_K if comprehensive else FINAL_TOP_K
    reranker = HRPolicyReranker()
    return reranker.rerank(
        question,
        candidates,
        top_k=final_top_k,
    )


def _prompt_from_results(question: str, results: list[dict]) -> str:
    context = format_context(results)
    return build_prompt(question, context)


def _prompt_from_candidates(question: str, candidates: list[dict]) -> str:
    if not candidates:
        return build_prompt(question, "")

    results = _rerank_candidates(question, candidates)
    return _prompt_from_results(question, results)


def _question_with_history(
    question: str,
    history: list[tuple[str, str]],
) -> str:
    if not history:
        return question

    lines = ["Recent conversation:"]
    for role, content in history:
        speaker = "User" if role == "user" else "Assistant"
        lines.append(f"{speaker}: {content}")
    lines.append(f"Current question: {question}")
    return "\n".join(lines)


def _answer_from_candidates(question: str, candidates: list[dict]) -> str:
    if not candidates:
        return "The information is not available " "in the provided policy context."

    prompt = _prompt_from_candidates(question, candidates)
    return generate_answer(prompt)


def prepare_answer_prompt(
    question: str,
    role: str = "public",
    history: list[tuple[str, str]] | None = None,
) -> PreparedAnswer:
    question, role = _validate_question_and_role(question, role)
    contextual_question = _question_with_history(question, history or [])
    candidates = retrieve_candidates(
        contextual_question,
        role,
    )
    if not candidates:
        return PreparedAnswer(prompt=None, sources=[])

    results = _rerank_candidates(contextual_question, candidates)
    sources = [
        {
            "document_name": result["document_name"],
            "source": result.get("source", "unknown"),
            "start_page": result["start_page"],
            "end_page": result["end_page"],
        }
        for result in results
    ]
    return PreparedAnswer(
        prompt=_prompt_from_results(contextual_question, results),
        sources=sources,
    )


def answer_question(
    question: str,
    role: str = "public",
    *,
    show_query_count: bool = False,
) -> str:
    question, role = _validate_question_and_role(question, role)
    candidates = retrieve_candidates(
        question,
        role,
        show_query_count=show_query_count,
    )
    return _answer_from_candidates(question, candidates)


if __name__ == "__main__":
    print("Available roles: hr, admin, employee, customer, support_agent, public")
    role = input("Search as role [public]: ").strip() or "public"
    question = input("Ask an HR policy question: ")

    try:
        answer = answer_question(question, role=role, show_query_count=True)
        print("\nAnswer:\n")
        print(answer)
    except Exception as exc:
        print(f"\nError while generating answer: {exc}")
