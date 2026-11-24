"""Extraction package."""

from .fingerprint import compute_claim_fingerprint
from .validator import QuotationValidationResult, validate_evidence_quotation

__all__ = [
    "compute_claim_fingerprint",
    "validate_evidence_quotation",
    "QuotationValidationResult",
]
