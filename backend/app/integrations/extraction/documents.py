from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from io import BytesIO

import fitz
from docx import Document as WordDocument

from app.integrations.contracts import IntegrationFailure


@dataclass(frozen=True)
class ExtractedPage:
    page_number: int | None
    location: str
    text: str


@dataclass(frozen=True)
class ExtractedChunk:
    chunk_index: int
    page_number: int | None
    section_label: str
    content: str
    content_hash: str
    start_offset: int
    end_offset: int
    token_count: int


class UnsupportedDocumentError(IntegrationFailure):
    def __init__(self) -> None:
        super().__init__(
            integration="document_extraction",
            code="unsupported_document",
            retryable=False,
        )


def _normalize_text(value: str) -> str:
    value = value.replace("\u00ad", "")
    value = re.sub(r"-\s*\n\s*", "", value)
    value = re.sub(r"[ \t]+\n", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def extract_document_pages(content: bytes, filename: str) -> list[ExtractedPage]:
    extension = filename.rpartition(".")[2].lower()
    if extension == "pdf" and content.startswith(b"%PDF-"):
        try:
            pdf = fitz.open(stream=content, filetype="pdf")
            try:
                if pdf.needs_pass:
                    raise IntegrationFailure(
                        integration="document_extraction",
                        code="document_password_protected",
                        retryable=False,
                    )
                return [
                    ExtractedPage(
                        page_number=index + 1,
                        location=f"Pagina {index + 1}",
                        text=_normalize_text(page.get_text("text")),
                    )
                    for index, page in enumerate(pdf)
                ]
            finally:
                pdf.close()
        except IntegrationFailure:
            raise
        except Exception as exc:
            raise IntegrationFailure(
                integration="document_extraction",
                code="invalid_pdf",
                retryable=False,
            ) from exc

    if extension == "docx" and content.startswith(b"PK"):
        try:
            document = WordDocument(BytesIO(content))
            paragraphs = [
                paragraph.text.strip()
                for paragraph in document.paragraphs
                if paragraph.text.strip()
            ]
            table_rows = [
                " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
                for table in document.tables
                for row in table.rows
            ]
            text = _normalize_text("\n".join([*paragraphs, *table_rows]))
            if not text:
                return []
            return [
                ExtractedPage(
                    page_number=None,
                    location=f"Parrafos 1-{len(paragraphs)}"
                    if paragraphs
                    else f"Tablas 1-{len(table_rows)}",
                    text=text,
                )
            ]
        except Exception as exc:
            raise IntegrationFailure(
                integration="document_extraction",
                code="invalid_docx",
                retryable=False,
            ) from exc

    raise UnsupportedDocumentError()


def chunk_document_pages(
    pages: list[ExtractedPage],
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> list[ExtractedChunk]:
    if chunk_size < 1 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap smaller than chunk_size")

    chunks: list[ExtractedChunk] = []
    for page in pages:
        text = _normalize_text(page.text)
        if not text:
            continue
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            if end < len(text):
                boundary = text.rfind(" ", start + chunk_size // 2, end)
                if boundary > start:
                    end = boundary
            raw_content = text[start:end]
            leading_whitespace = len(raw_content) - len(raw_content.lstrip())
            content = raw_content.strip()
            if content:
                content_start = start + leading_whitespace
                chunks.append(
                    ExtractedChunk(
                        chunk_index=len(chunks),
                        page_number=page.page_number,
                        section_label=page.location,
                        content=content,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        start_offset=content_start,
                        end_offset=content_start + len(content),
                        token_count=max(1, len(content) // 4),
                    )
                )
            if end >= len(text):
                break
            start = max(start + 1, end - overlap)
    return chunks
