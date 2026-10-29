from qdrant_client import models


def build_payload_filter(
    query_filter: models.Filter | None = None,
    *,
    source: str | None = None,
    document_name: str | None = None,
    role: str | None = None,
    min_page: int | None = None,
    max_page: int | None = None,
) -> models.Filter | None:
    """Combine common metadata filters, including public chunks for a role."""
    conditions: list[models.Condition] = []

    for field_name, value in (
        ("source", source),
        ("document_name", document_name),
    ):
        if value is not None:
            if not value.strip():
                raise ValueError(f"{field_name} cannot be empty")
            conditions.append(
                models.FieldCondition(
                    key=field_name,
                    match=models.MatchValue(value=value),
                )
            )

    if role is not None:
        if not role.strip():
            raise ValueError("role cannot be empty")
        if role == "public":
            conditions.append(
                models.FieldCondition(
                    key="source",
                    match=models.MatchValue(value="public"),
                )
            )
            conditions.append(
                models.IsEmptyCondition(
                    is_empty=models.PayloadField(key="allowed_roles")
                )
            )
        else:
            conditions.append(
                models.Filter(
                    should=[
                        models.FieldCondition(
                            key="allowed_roles",
                            match=models.MatchAny(any=[role]),
                        ),
                        models.Filter(
                            must=[
                                models.FieldCondition(
                                    key="source",
                                    match=models.MatchValue(value="public"),
                                ),
                                models.IsEmptyCondition(
                                    is_empty=models.PayloadField(key="allowed_roles")
                                ),
                            ]
                        ),
                    ]
                )
            )

    if min_page is not None:
        if min_page < 1:
            raise ValueError("min_page must be at least 1")
        conditions.append(
            models.FieldCondition(
                key="end_page",
                range=models.Range(gte=min_page),
            )
        )

    if max_page is not None:
        if max_page < 1:
            raise ValueError("max_page must be at least 1")
        conditions.append(
            models.FieldCondition(
                key="start_page",
                range=models.Range(lte=max_page),
            )
        )

    if min_page is not None and max_page is not None and min_page > max_page:
        raise ValueError("min_page cannot exceed max_page")

    if query_filter is not None:
        conditions.insert(0, query_filter)

    if not conditions:
        return None

    return models.Filter(must=conditions)


def validate_access_metadata(chunk: dict[str, object]) -> None:
    """Require source and allowed_roles fields before storing a chunk."""
    source = chunk.get("source")
    allowed_roles = chunk.get("allowed_roles")

    if not isinstance(source, str) or not source.strip():
        raise ValueError(f"Chunk {chunk.get('chunk_id')} has no valid source")

    if not isinstance(allowed_roles, list) or any(
        not isinstance(role, str) or not role.strip() for role in allowed_roles
    ):
        raise ValueError(
            f"Chunk {chunk.get('chunk_id')} has invalid allowed_roles metadata"
        )
