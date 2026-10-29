from sentence_transformers import CrossEncoder

MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class HRPolicyReranker:
    """Rerank retrieved HR policy chunks against a user question."""

    def __init__(self) -> None:
        self.model = CrossEncoder(MODEL_NAME)

    def rerank(
        self,
        question: str,
        candidates: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        question = question.strip()

        if not question:
            raise ValueError("Search question cannot be empty")

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        if not candidates:
            return []

        pairs = [(question, candidate["text"]) for candidate in candidates]

        scores = self.model.predict(pairs)

        reranked = []

        for candidate, score in zip(candidates, scores):
            result = candidate.copy()
            result["rerank_score"] = float(score)
            reranked.append(result)

        reranked.sort(
            key=lambda result: result["rerank_score"],
            reverse=True,
        )

        return reranked[:top_k]
