"""Deterministic Claim Fingerprinting."""

import hashlib
from typing import Optional


def compute_claim_fingerprint(
    subject_id: str,
    predicate: str,
    object_id: str,
    polarity: str = "affirmed",
    temporal_scope: Optional[str] = None,
) -> str:
    """Computes a deterministic, collision-resistant SHA-256 fingerprint for a claim.

    Normalizes subject, predicate, object, polarity, and temporal scope into a canonical
    string representation before digesting.
    """
    norm_subj = subject_id.strip().lower()
    norm_pred = predicate.strip().upper()
    norm_obj = object_id.strip().lower()
    norm_pol = polarity.strip().lower()
    norm_temp = temporal_scope.strip() if temporal_scope else ""

    payload = f"{norm_subj}|{norm_pred}|{norm_obj}|{norm_pol}|{norm_temp}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"clm_{digest}"
