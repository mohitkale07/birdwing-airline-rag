import logging
from pathlib import Path
from typing import TypedDict

import pymupdf

logger = logging.getLogger(__name__)


class PageRecord(TypedDict):
    document_name: str
    page_number: int
    text: str


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be extracted reliably."""


def extract_pdf(pdf_path: Path) -> list[PageRecord]:
    """
    Extract text page by page while preserving source metadata.

    Args:
        pdf_path: Path to the source PDF.

    Returns:
        A list containing one record per PDF page.

    Raises:
        FileNotFoundError: If the PDF does not exist.
        ValueError: If the path is invalid or the file is empty.
        PDFExtractionError: If the PDF cannot be opened or processed.
    """
    pdf_path = pdf_path.resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    if not pdf_path.is_file():
        raise ValueError(f"Expected a PDF file: {pdf_path}")

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file: {pdf_path}")

    if pdf_path.stat().st_size == 0:
        raise ValueError(f"PDF file is empty: {pdf_path}")

    records: list[PageRecord] = []
    empty_pages: list[int] = []

    try:
        with pymupdf.open(pdf_path) as document:
            if document.is_encrypted:
                raise PDFExtractionError(
                    f"Encrypted PDF requires authorized password handling: "
                    f"{pdf_path.name}"
                )

            if len(document) == 0:
                raise PDFExtractionError(f"PDF contains no pages: {pdf_path.name}")

            for page_index, page in enumerate(document):
                try:
                    text = page.get_text("text").strip()
                except pymupdf.MuPDFException as exc:
                    raise PDFExtractionError(
                        f"Failed to extract page {page_index + 1} "
                        f"from {pdf_path.name}"
                    ) from exc

                if not text:
                    empty_pages.append(page_index + 1)

                records.append(
                    {
                        "document_name": pdf_path.name,
                        "page_number": page_index + 1,
                        "text": text,
                    }
                )

    except PDFExtractionError:
        raise
    except (pymupdf.FileDataError, pymupdf.MuPDFException) as exc:
        raise PDFExtractionError(f"Could not open or process PDF: {pdf_path}") from exc

    if empty_pages:
        logger.warning(
            "No extractable text found on %d page(s) of %s: %s. "
            "These pages may be blank or scanned.",
            len(empty_pages),
            pdf_path.name,
            empty_pages,
        )

    total_characters = sum(len(record["text"]) for record in records)

    logger.info(
        "Extracted %d pages and %d characters from %s",
        len(records),
        total_characters,
        pdf_path.name,
    )

    return records


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    project_root = Path(__file__).resolve().parents[2]
    pdf_path = project_root / "data" / "raw" / "airline_hr_policy.pdf"

    try:
        pages = extract_pdf(pdf_path)
    except (FileNotFoundError, ValueError, PDFExtractionError):
        logger.exception("PDF extraction failed")
        raise SystemExit(1)

    output_dir = project_root / "data" / "processed"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / "extracted_pages.txt"

    with output_path.open("w", encoding="utf-8") as output_file:
        for record in pages:
            output_file.write(f"--- Page {record['page_number']} ---\n")
            output_file.write(record["text"])
            output_file.write("\n\n")

    print(f"Pages extracted: {len(pages)}")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
