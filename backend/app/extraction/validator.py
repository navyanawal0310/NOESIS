"""Evidence Quotation and Text Offset Validation."""


class QuotationValidationResult:
    """Outcome of quotation span verification."""

    def __init__(self, is_valid: bool, reason: str, matched_text: str = ""):
        self.is_valid = is_valid
        self.reason = reason
        self.matched_text = matched_text

    def to_dict(self):
        return {
            "is_valid": self.is_valid,
            "reason": self.reason,
            "matched_text": self.matched_text,
            "disclaimer": "Quotation matching verifies text existence, not semantic claim correctness.",
        }


def validate_evidence_quotation(
    raw_text: str,
    quote: str,
    start_offset: int,
    end_offset: int,
) -> QuotationValidationResult:
    """Verifies that an evidence record's quotation exactly matches the source document text

    at the specified character offsets.

    IMPORTANT NOTE:
    Quotation matching proves that the exact words exist in the document at that position,
    but does not in itself guarantee that the semantic claim extracted from it is true or valid.
    """
    if not raw_text:
        return QuotationValidationResult(False, "Document text is empty")

    if start_offset < 0 or end_offset > len(raw_text) or start_offset >= end_offset:
        return QuotationValidationResult(
            False,
            f"Offsets [{start_offset}:{end_offset}] out of bounds for text length {len(raw_text)}",
        )

    extracted_slice = raw_text[start_offset:end_offset]

    if extracted_slice == quote:
        return QuotationValidationResult(True, "Exact character match confirmed", extracted_slice)

    # Normalize whitespace check as fallback for minor carriage return differences
    norm_slice = " ".join(extracted_slice.split())
    norm_quote = " ".join(quote.split())
    if norm_slice == norm_quote:
        return QuotationValidationResult(
            True,
            "Normalized whitespace match confirmed",
            extracted_slice,
        )

    # Substring search check
    pos = raw_text.find(quote)
    if pos != -1:
        return QuotationValidationResult(
            False,
            f"Offset mismatch: expected [{start_offset}:{end_offset}], found at [{pos}:{pos + len(quote)}]",
            extracted_slice,
        )

    return QuotationValidationResult(
        False,
        "Quotation not found in source text",
        extracted_slice,
    )
