"""Explainable Confidence Scoring Heuristic.

Implements the PRD Section 9 confidence heuristic:
C(e) = 0.35*Q + 0.30*S + 0.20*A + 0.15*V
and path confidence:
C(P) = min_{e in P} C(e)
"""

from typing import List

from backend.app.ontology.models import Claim, Evidence


def compute_claim_confidence(
    claim: Claim,
    evidence_list: List[Evidence],
    has_contradiction: bool = False,
    all_quotes_valid: bool = True,
) -> float:
    """Computes an explainable support score C(e) for a claim.

    Variables:
      Q: Evidence quality indicator [0, 1]
      S: Independent-source support count (normalized: min(1.0, num_docs / 2.0))
      A: Agreement among eligible sources (1.0 if undisputed, 0.5 if contradicted)
      V: Evidence validation indicator (1.0 if exact text spans match)
    """
    if not evidence_list:
        return 0.0

    # Q: Average confidence across evidence records
    q = sum(ev.confidence for ev in evidence_list) / len(evidence_list)
    q = max(0.0, min(1.0, q))

    # S: Independent distinct source documents count
    doc_ids = {ev.document_id for ev in evidence_list}
    s = min(1.0, len(doc_ids) / 2.0)

    # A: Source agreement
    if has_contradiction or len(claim.contradiction_ids) > 0:
        a = 0.4
    else:
        a = 1.0

    # V: Exact text verification indicator
    v = 1.0 if all_quotes_valid else 0.2

    confidence = (0.35 * q) + (0.30 * s) + (0.20 * a) + (0.15 * v)
    return round(max(0.0, min(1.0, confidence)), 4)


def compute_path_confidence(segment_confidences: List[float]) -> float:
    """Computes path confidence as the weakest-link minimum: C(P) = min_{e in P} C(e)."""
    if not segment_confidences:
        return 0.0
    return min(segment_confidences)
