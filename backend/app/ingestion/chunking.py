"""Provenance-Preserving Document Chunking."""

import re
from typing import List

from pydantic import BaseModel, Field

from backend.app.config import settings
from backend.app.ingestion.parser import PageSpan, ParsedDocument


class DocumentChunk(BaseModel):
    """Discrete text chunk with exact provenance offsets mapped to the source document."""

    chunk_id: str = Field(..., description="Unique chunk identifier (e.g. chk_doc123_01)")
    document_id: str = Field(..., description="Origin document ID")
    chunk_index: int = Field(..., description="0-based sequence index")
    text: str = Field(..., description="Chunk text content")
    char_offset_start: int = Field(..., ge=0, description="Exact start index in raw_text")
    char_offset_end: int = Field(..., ge=0, description="Exact end index in raw_text")
    page_start: int = Field(default=1, description="Primary starting page number")
    page_end: int = Field(default=1, description="Primary ending page number")
    approx_tokens: int = Field(..., description="Estimated token count (~4 chars per token)")


class DocumentChunker:
    """Splits document text into overlapping chunks along natural syntactic boundaries

    while strictly preserving character offsets into the source document.
    """

    def __init__(
        self,
        chunk_size_chars: int = None,
        chunk_overlap_chars: int = None,
    ):
        self.chunk_size = chunk_size_chars or settings.CHUNK_SIZE_CHARS
        self.chunk_overlap = chunk_overlap_chars or settings.CHUNK_OVERLAP_CHARS

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be strictly less than chunk_size")

    def _determine_pages(self, char_start: int, char_end: int, page_spans: List[PageSpan]) -> tuple[int, int]:
        """Resolves the 1-based page numbers covering [char_start:char_end]."""
        if not page_spans:
            return 1, 1

        start_page = page_spans[0].page_number
        end_page = page_spans[-1].page_number

        for span in page_spans:
            if span.char_start <= char_start < span.char_end:
                start_page = span.page_number
            if span.char_start < char_end <= span.char_end:
                end_page = span.page_number

        return start_page, end_page

    def chunk_document(self, doc: ParsedDocument) -> List[DocumentChunk]:
        """Chunks a ParsedDocument, preserving exact character offsets and page references."""
        raw_text = doc.raw_text
        text_len = len(raw_text)

        if text_len == 0:
            return []

        # If document is smaller than target chunk size, return single chunk
        if text_len <= self.chunk_size:
            p_start, p_end = self._determine_pages(0, text_len, doc.page_spans)
            return [
                DocumentChunk(
                    chunk_id=f"chk_{doc.document_id}_01",
                    document_id=doc.document_id,
                    chunk_index=0,
                    text=raw_text,
                    char_offset_start=0,
                    char_offset_end=text_len,
                    page_start=p_start,
                    page_end=p_end,
                    approx_tokens=max(1, text_len // 4),
                )
            ]

        chunks: List[DocumentChunk] = []
        current_start = 0
        chunk_idx = 0

        while current_start < text_len:
            target_end = min(current_start + self.chunk_size, text_len)

            if target_end < text_len:
                # Seek natural boundary: paragraph break, then sentence break, then whitespace
                search_window = raw_text[current_start + self.chunk_size // 2 : target_end]
                # Look for paragraph break
                para_match = [m.start() for m in re.finditer(r"\n\s*\n", search_window)]
                if para_match:
                    split_offset = current_start + self.chunk_size // 2 + para_match[-1] + 2
                else:
                    # Look for sentence boundary
                    sent_match = [m.start() for m in re.finditer(r"[.!?]\s+", search_window)]
                    if sent_match:
                        split_offset = current_start + self.chunk_size // 2 + sent_match[-1] + 2
                    else:
                        # Fallback to whitespace
                        space_match = [m.start() for m in re.finditer(r"\s+", search_window)]
                        if space_match:
                            split_offset = current_start + self.chunk_size // 2 + space_match[-1] + 1
                        else:
                            split_offset = target_end
                actual_end = min(split_offset, text_len)
            else:
                actual_end = text_len

            chunk_text = raw_text[current_start:actual_end]
            p_start, p_end = self._determine_pages(current_start, actual_end, doc.page_spans)

            chunks.append(
                DocumentChunk(
                    chunk_id=f"chk_{doc.document_id}_{chunk_idx + 1:02d}",
                    document_id=doc.document_id,
                    chunk_index=chunk_idx,
                    text=chunk_text,
                    char_offset_start=current_start,
                    char_offset_end=actual_end,
                    page_start=p_start,
                    page_end=p_end,
                    approx_tokens=max(1, len(chunk_text) // 4),
                )
            )

            chunk_idx += 1
            if actual_end >= text_len:
                break

            # Advance by step size (chunk_length - overlap)
            step = actual_end - current_start - self.chunk_overlap
            if step <= 0:
                step = max(1, self.chunk_size - self.chunk_overlap)
            current_start += step

        return chunks
