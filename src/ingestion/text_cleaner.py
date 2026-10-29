import re

# Remove repeated boilerplate and a text artifact found in the source PDF.
FOOTER_PATTERNS = [
    re.compile(r"(?im)^[ \t]*\S+@\S+\.\S+[ \t]*$"),
    re.compile(r"(?im)^[ \t]*This file is meant for personal use by .*$"),
    re.compile(
        r"(?im)^[ \t]*Sharing or publishing the contents in part or full is liable for legal action\.?[ \t]*$"
    ),
    re.compile(r"(?im)^[ \t]*2P5FMGJZNO[ \t]*$"),
]


def clean_page_text(text: str) -> str:
    """Remove known PDF boilerplate and normalize extracted text."""
    # PyMuPDF preserves zero-width separators after bullets and line endings.
    text = text.replace("\u200b", "")

    for pattern in FOOTER_PATTERNS:
        text = pattern.sub("", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]
    cleaned_text = "\n".join(
        line for i, line in enumerate(lines) if line or (i > 0 and lines[i - 1])
    )

    return cleaned_text.strip()
