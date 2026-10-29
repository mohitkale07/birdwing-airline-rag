from pathlib import Path

from src.retrieval.search import USER_ROLES, HybridHRPolicyRetriever
from src.retrieval.reranker import HRPolicyReranker
from src.generation.context_builder import format_context
from src.generation.prompt_builder import build_prompt
from src.generation.llm_client import generate_answer

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
) -> list[dict]:
    """Retrieve role-filtered chunks for a question."""
    question, role = _validate_question_and_role(question, role)
    project_root = Path(__file__).resolve().parents[2]
    comprehensive = _is_comprehensive_question(question)
    candidate_k = COMPREHENSIVE_CANDIDATE_K if comprehensive else CANDIDATE_K

    retriever = HybridHRPolicyRetriever(project_root)
    try:
        return retriever.search(
            question,
            top_k=candidate_k,
            role=role,
        )
    finally:
        retriever.close()


def _answer_from_candidates(question: str, candidates: list[dict]) -> str:
    comprehensive = _is_comprehensive_question(question)
    final_top_k = COMPREHENSIVE_TOP_K if comprehensive else FINAL_TOP_K

    if not candidates:
        return "The information is not available " "in the provided policy context."

    reranker = HRPolicyReranker()
    results = reranker.rerank(
        question,
        candidates,
        top_k=final_top_k,
    )

    context = format_context(results)
    prompt = build_prompt(question, context)
    return generate_answer(prompt)


def answer_question(question: str, role: str = "public") -> str:
    question, role = _validate_question_and_role(question, role)
    candidates = retrieve_candidates(question, role)
    return _answer_from_candidates(question, candidates)


if __name__ == "__main__":
    print("Available roles: hr, admin, employee, customer, support_agent, public")
    role = input("Search as role [public]: ").strip() or "public"
    question = input("Ask an HR policy question: ")

    try:
        answer = answer_question(question, role=role)
        print("\nAnswer:\n")
        print(answer)
    except Exception as exc:
        print(f"\nError while generating answer: {exc}")
