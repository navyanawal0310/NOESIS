"""Unit Tests for Document Parsing, Page Boundary Tracking, and Chunking."""

import fitz
import pytest

from backend.app.ingestion.chunking import DocumentChunker
from backend.app.ingestion.parser import (
    DocumentParser,
    ParsedDocument,
    UnsupportedDocumentError,
)


def test_txt_and_md_parsing():
    """Verifies that plain text and markdown documents are correctly parsed with content hashing."""
    txt_content = b"NOESIS is a neural-ontological evidence synthesis system.\nIt tracks claims deterministically."
    parsed_txt = DocumentParser.parse_file("overview.txt", txt_content)
    assert parsed_txt.source_type == "txt"
    assert parsed_txt.total_chars == len(txt_content.decode("utf-8"))
    assert parsed_txt.total_pages == 1
    assert len(parsed_txt.content_hash) == 64
    assert "NOESIS is a neural-ontological" in parsed_txt.raw_text

    md_content = b"# Architecture\n\n- Evidence-native\n- Dual-store resilience"
    parsed_md = DocumentParser.parse_file("arch.md", md_content)
    assert parsed_md.source_type == "md"
    assert parsed_md.total_pages == 1
    assert "Dual-store resilience" in parsed_md.raw_text


def test_pdf_parsing_with_pymupdf():
    """Creates a multi-page PDF in-memory using PyMuPDF and verifies page span offset alignment."""
    doc = fitz.open()

    page1_text = "Page 1: Dr. Elena Vance initiated Project Aetheris in Geneva.\n"
    page2_text = "Page 2: The neural-symbolic framework achieved zero-shot reasoning.\n"

    p1 = doc.new_page()
    p1.insert_text((50, 50), page1_text)

    p2 = doc.new_page()
    p2.insert_text((50, 50), page2_text)

    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = DocumentParser.parse_file("test_multi.pdf", pdf_bytes)
    assert parsed.source_type == "pdf"
    assert parsed.total_pages == 2
    assert len(parsed.page_spans) == 2

    # Verify that each page span directly slices the extracted raw_text
    span1 = parsed.page_spans[0]
    span2 = parsed.page_spans[1]

    assert span1.page_number == 1
    page1_slice = parsed.raw_text[span1.char_start:span1.char_end]
    assert "Dr. Elena Vance" in page1_slice

    assert span2.page_number == 2
    page2_slice = parsed.raw_text[span2.char_start:span2.char_end]
    assert "neural-symbolic framework" in page2_slice


def test_empty_and_scanned_pdf_detection():
    """Ensures empty documents or scanned PDFs without extractable text are identified."""
    doc = fitz.open()
    doc.new_page()  # Blank page without text
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = DocumentParser.parse_file("blank.pdf", pdf_bytes)
    assert parsed.is_scanned_ocr_required is True
    assert parsed.total_chars == 0


def test_unsupported_file_format():
    """Verifies that unsupported file extensions are rejected."""
    with pytest.raises(UnsupportedDocumentError) as exc_info:
        DocumentParser.parse_file("document.docx", b"PK\x03\x04...")
    assert "Unsupported file format" in str(exc_info.value)


def test_document_chunker_offset_exactness():
    """Verifies that chunks maintain exact character offsets back to the raw source text."""
    paragraphs = [
        "First paragraph describes the origins of the Aetheris consortium founded in 2021 by Dr. Elena Vance.",
        "Second paragraph details the collaborative research conducted alongside Dr. Alyssa Vance at Nexus Research.",
        "Third paragraph notes that Julian Mercer explicitly disputed the validity of the benchmark results in 2024.",
    ]
    raw_text = "\n\n".join(paragraphs)

    parsed = ParsedDocument(
        document_id="doc_test_chunking",
        filename="test_chunking.txt",
        source_type="txt",
        content_hash=DocumentParser.compute_sha256(raw_text.encode("utf-8")),
        raw_text=raw_text,
        total_pages=1,
        total_chars=len(raw_text),
        ingestion_timestamp="2026-11-24T00:00:00Z",
    )

    chunker = DocumentChunker(chunk_size_chars=120, chunk_overlap_chars=30)
    chunks = chunker.chunk_document(parsed)

    assert len(chunks) >= 2
    for chunk in chunks:
        # Crucial invariant: raw_text[char_offset_start:char_offset_end] MUST equal chunk.text exactly
        assert parsed.raw_text[chunk.char_offset_start:chunk.char_offset_end] == chunk.text
        assert chunk.document_id == parsed.document_id
        assert chunk.chunk_id.startswith("chk_")
