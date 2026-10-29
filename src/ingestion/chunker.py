from dataclasses import dataclass
from hashlib import sha256

from docling.chunking import HybridChunker
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
from docling_core.types.doc import DoclingDocument

from src.ingestion.text_cleaner import clean_page_text

EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
MAX_CHUNK_TOKENS = 220


@dataclass(frozen=True, slots=True)
class TextChunk:
    chunk_id: str
    document_name: str
    start_page: int
    end_page: int
    chunk_index: int
    text: str
    source: str
    allowed_roles: list[str]


def chunk_docling_document(
    document: DoclingDocument,
    document_name: str,
    max_tokens: int = MAX_CHUNK_TOKENS,
    source: str = "hr",
    allowed_roles: list[str] | None = None,
) -> list[TextChunk]:
    """Create heading-aware, token-bounded chunks from a Docling document."""
    if not document_name.strip():
        raise ValueError("document_name must not be empty")
    if max_tokens <= 0:
        raise ValueError("max_tokens must be greater than zero")
    if not source.strip():
        raise ValueError("source must not be empty")

    roles = ["hr", "admin"] if allowed_roles is None else list(allowed_roles)
    if any(not role.strip() for role in roles):
        raise ValueError("allowed_roles must contain non-empty role names")

    tokenizer = HuggingFaceTokenizer.from_pretrained(
        model_name=EMBEDDING_MODEL_NAME,
        max_tokens=max_tokens,
    )
    chunker = HybridChunker(tokenizer=tokenizer)
    chunks: list[TextChunk] = []

    for docling_chunk in chunker.chunk(dl_doc=document):
        # contextualize includes section headings, which helps retrieval when a
        # chunk contains only the body of a policy section.
        text = clean_page_text(chunker.contextualize(chunk=docling_chunk))
        if not text:
            continue

        page_numbers = sorted(
            {
                int(provenance.page_no)
                for item in docling_chunk.meta.doc_items
                for provenance in (getattr(item, "prov", None) or [])
            }
        )
        if not page_numbers:
            raise ValueError(
                "Docling produced a chunk without page provenance; "
                "cannot safely attach source metadata"
            )

        chunk_index = len(chunks)
        start_page = page_numbers[0]
        end_page = page_numbers[-1]
        identity = f"{document_name}:{chunk_index}:{start_page}:{end_page}:{text}"
        chunks.append(
            TextChunk(
                chunk_id=sha256(identity.encode("utf-8")).hexdigest(),
                document_name=document_name,
                start_page=start_page,
                end_page=end_page,
                chunk_index=chunk_index,
                text=text,
                source=source.strip(),
                allowed_roles=roles.copy(),
            )
        )

    return chunks
