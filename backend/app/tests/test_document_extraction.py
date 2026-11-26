from io import BytesIO

import fitz
import pytest
from docx import Document

from app.integrations.extraction.documents import (
    UnsupportedDocumentError,
    chunk_document_pages,
    extract_document_pages,
)


def _pdf_bytes() -> bytes:
    pdf = fitz.open()
    pdf.new_page().insert_text((72, 72), "Bases administrativas de la licitacion")
    pdf.new_page().insert_text((72, 72), "El plazo de entrega es de treinta dias")
    return pdf.tobytes()


def test_pdf_extraction_retains_original_page_numbers():
    pages = extract_document_pages(_pdf_bytes(), "bases.pdf")

    assert [page.page_number for page in pages] == [1, 2]
    assert "Bases administrativas" in pages[0].text
    assert "treinta dias" in pages[1].text


def test_docx_extraction_retains_paragraph_location():
    document = Document()
    document.add_paragraph("Requisitos tecnicos")
    document.add_paragraph("La empresa debe presentar experiencia.")
    buffer = BytesIO()
    document.save(buffer)

    pages = extract_document_pages(buffer.getvalue(), "requisitos.docx")

    assert len(pages) == 1
    assert pages[0].page_number is None
    assert "parrafos 1-2" in pages[0].location.lower()
    assert "presentar experiencia" in pages[0].text


def test_chunking_preserves_page_and_offsets():
    pages = extract_document_pages(_pdf_bytes(), "bases.pdf")

    chunks = chunk_document_pages(pages, chunk_size=80, overlap=10)

    assert {chunk.page_number for chunk in chunks} == {1, 2}
    assert all(chunk.start_offset is not None for chunk in chunks)
    assert all(chunk.end_offset >= chunk.start_offset for chunk in chunks)
    for chunk in chunks:
        page = pages[chunk.page_number - 1]
        assert page.text[chunk.start_offset : chunk.end_offset] == chunk.content


def test_unsupported_document_format_is_rejected():
    with pytest.raises(UnsupportedDocumentError):
        extract_document_pages(b"not a document", "bases.txt")
