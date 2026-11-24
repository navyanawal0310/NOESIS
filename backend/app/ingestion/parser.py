"""Document Parser for PDF, TXT, and Markdown Formats."""

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown"}


class PageSpan(BaseModel):
    """Character offsets corresponding to a physical or logical document page."""

    page_number: int
    char_start: int
    char_end: int


class ParsedDocument(BaseModel):
    """Normalized payload resulting from document file ingestion."""

    document_id: str
    filename: str
    source_type: str
    content_hash: str
    raw_text: str
    page_spans: List[PageSpan] = Field(default_factory=list)
    total_pages: int = 1
    total_chars: int = 0
    ingestion_timestamp: str
    is_scanned_ocr_required: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UnsupportedDocumentError(Exception):
    """Raised when a file format is unsupported or contains no extractable text."""

    pass


class DocumentParser:
    """Extracts text, character offsets, and page boundaries from source files."""

    @staticmethod
    def compute_sha256(content_bytes: bytes) -> str:
        """Computes SHA-256 digest over binary content."""
        return hashlib.sha256(content_bytes).hexdigest()

    @classmethod
    def parse_file(
        cls,
        filename: str,
        content_bytes: bytes,
        document_id: Optional[str] = None,
        corpus: str = "real",
    ) -> ParsedDocument:
        """Parses a file payload into a structured ParsedDocument with page boundaries."""
        ext = Path(filename).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            raise UnsupportedDocumentError(
                f"Unsupported file format '{ext}'. Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        content_hash = cls.compute_sha256(content_bytes)
        doc_id = document_id or f"doc_{content_hash[:12]}"
        now_iso = datetime.now(timezone.utc).isoformat()

        if ext == ".pdf":
            return cls._parse_pdf(doc_id, filename, content_bytes, content_hash, now_iso, corpus)
        elif ext in {".txt", ".md", ".markdown"}:
            return cls._parse_text(doc_id, filename, content_bytes, content_hash, now_iso, ext[1:], corpus)
        else:
            raise UnsupportedDocumentError(f"Handler for extension '{ext}' not found.")

    @classmethod
    def _parse_pdf(
        cls,
        doc_id: str,
        filename: str,
        content_bytes: bytes,
        content_hash: str,
        timestamp: str,
        corpus: str,
    ) -> ParsedDocument:
        """Extracts text from PDF using PyMuPDF (fitz) with per-page character tracking."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            raise UnsupportedDocumentError("PyMuPDF (fitz) is not installed in the runtime environment.")

        try:
            pdf_doc = fitz.open(stream=content_bytes, filetype="pdf")
        except Exception as e:
            raise UnsupportedDocumentError(f"Failed to open PDF document: {str(e)}")

        total_pages = len(pdf_doc)
        if total_pages == 0:
            raise UnsupportedDocumentError("PDF document contains 0 pages.")

        page_texts: List[str] = []
        page_spans: List[PageSpan] = []
        cumulative_len = 0

        for page_idx in range(total_pages):
            page = pdf_doc[page_idx]
            text = page.get_text() or ""
            # Normalize carriage returns
            norm_text = text.replace("\r\n", "\n")

            start_char = cumulative_len
            end_char = start_char + len(norm_text)
            page_spans.append(PageSpan(page_number=page_idx + 1, char_start=start_char, char_end=end_char))

            page_texts.append(norm_text)
            cumulative_len = end_char

        pdf_doc.close()

        full_text = "".join(page_texts)

        # Detect scanned or empty PDF
        if not full_text.strip():
            return ParsedDocument(
                document_id=doc_id,
                filename=filename,
                source_type="pdf",
                content_hash=content_hash,
                raw_text="",
                page_spans=page_spans,
                total_pages=total_pages,
                total_chars=0,
                ingestion_timestamp=timestamp,
                is_scanned_ocr_required=True,
                metadata={
                    "corpus": corpus,
                    "error": "Scanned document with no extractable text; OCR required but unavailable",
                },
            )

        return ParsedDocument(
            document_id=doc_id,
            filename=filename,
            source_type="pdf",
            content_hash=content_hash,
            raw_text=full_text,
            page_spans=page_spans,
            total_pages=total_pages,
            total_chars=len(full_text),
            ingestion_timestamp=timestamp,
            is_scanned_ocr_required=False,
            metadata={"corpus": corpus, "format": "pdf"},
        )

    @classmethod
    def _parse_text(
        cls,
        doc_id: str,
        filename: str,
        content_bytes: bytes,
        content_hash: str,
        timestamp: str,
        source_type: str,
        corpus: str,
    ) -> ParsedDocument:
        """Parses plain text or Markdown files."""
        try:
            raw_text = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content_bytes.decode("latin-1")
            except Exception as e:
                raise UnsupportedDocumentError(f"Text encoding not supported: {str(e)}")

        norm_text = raw_text.replace("\r\n", "\n")

        if not norm_text.strip():
            raise UnsupportedDocumentError("Document contains no readable text content.")

        page_spans = [PageSpan(page_number=1, char_start=0, char_end=len(norm_text))]

        return ParsedDocument(
            document_id=doc_id,
            filename=filename,
            source_type=source_type,
            content_hash=content_hash,
            raw_text=norm_text,
            page_spans=page_spans,
            total_pages=1,
            total_chars=len(norm_text),
            ingestion_timestamp=timestamp,
            is_scanned_ocr_required=False,
            metadata={"corpus": corpus, "format": source_type},
        )
