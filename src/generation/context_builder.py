def format_context(results: list[dict]) -> str:
    passages = []

    for result in results:
        start_page = result["start_page"]
        end_page = result["end_page"]
        page_range = str(start_page)
        if end_page != start_page:
            page_range += f"–{end_page}"
        passage = (
            f"[Document: {result['document_name']}; "
            f"Category: {result.get('source', 'unknown')}; "
            f"Pages: {page_range}]\n"
            f"{result['text']}"
        )

        passages.append(passage)

    return "\n\n---\n\n".join(passages)
