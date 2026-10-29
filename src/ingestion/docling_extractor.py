from pathlib import Path

from docling.document_converter import DocumentConverter
from docling_core.types.doc import DoclingDocument

from src.ingestion.pdf_extractor import PageRecord


def convert_pdf_with_docling(
    pdf_path: Path,
    converter: DocumentConverter | None = None,
) -> DoclingDocument:
    """Convert a PDF into Docling's structured document representation."""

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    active_converter = converter if converter is not None else DocumentConverter()
    return active_converter.convert(str(pdf_path)).document


def extract_pdf_with_docling(pdf_path: Path) -> list[PageRecord]:
    """Extract structured text into page-level records using Docling."""
    document = convert_pdf_with_docling(pdf_path)

    page_text: dict[int, list[str]] = {
        int(page.page_no): [] for page in document.pages.values()
    }

    for item, _level in document.iterate_items():
        text = getattr(item, "text", None)
        provenance = getattr(item, "prov", None)

        if not text or not text.strip() or not provenance:
            continue

        for source in provenance:
            page_number = int(source.page_no)

            if page_number in page_text:
                page_text[page_number].append(text.strip())

    return [
        {
            "document_name": pdf_path.name,
            "page_number": page_number,
            "text": "\n\n".join(text_parts),
        }
        for page_number, text_parts in sorted(page_text.items())
    ]
