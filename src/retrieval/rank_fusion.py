from typing import Any


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict[str, Any]]],
    top_k: int | None = None,
    rank_constant: int = 60,
) -> list[dict[str, Any]]:
    """Combine ranked chunk lists, deduplicating by chunk ID."""
    if rank_constant <= 0:
        raise ValueError("rank_constant must be greater than zero")

    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be greater than zero")

    fused: dict[tuple[str, ...], dict[str, Any]] = {}

    for ranked_list in ranked_lists:
        seen_in_list = set()
        for rank, candidate in enumerate(ranked_list, start=1):
            chunk_id = candidate.get("chunk_id")
            if chunk_id is None:
                key = (
                    "payload",
                    str(candidate.get("document_name")),
                    str(candidate.get("start_page")),
                    str(candidate.get("end_page")),
                    str(candidate.get("text", "")),
                )
            else:
                key = ("chunk_id", str(chunk_id))

            if key in seen_in_list:
                continue
            seen_in_list.add(key)

            if key not in fused:
                fused[key] = {**candidate, "rrf_score": 0.0}

            fused[key]["rrf_score"] += 1 / (rank_constant + rank)

    results = sorted(
        fused.values(),
        key=lambda candidate: candidate["rrf_score"],
        reverse=True,
    )
    return results[:top_k] if top_k is not None else results
