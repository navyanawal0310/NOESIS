"""Tests for Evidence-Centric Ontology, Claim Fingerprinting, and Quotation Validation."""

from backend.app.extraction.fingerprint import compute_claim_fingerprint
from backend.app.extraction.validator import validate_evidence_quotation
from backend.app.ontology.models import Claim, Polarity


def test_claim_fingerprint_determinism():
    """Verify that identical semantic fields yield identical fingerprints regardless of casing."""
    fp1 = compute_claim_fingerprint(
        subject_id="ent_alyssa_vance",
        predicate="FOUNDED",
        object_id="ent_cognitive_dyn",
        polarity="affirmed",
        temporal_scope="2022",
    )
    fp2 = compute_claim_fingerprint(
        subject_id="  ENT_ALYSSA_VANCE  ",
        predicate="founded",
        object_id="Ent_Cognitive_Dyn",
        polarity="AFFIRMED",
        temporal_scope="2022",
    )
    assert fp1 == fp2, "Fingerprints must be deterministic across whitespace and casing normalization"

    # Different polarity must produce a distinct fingerprint
    fp_negated = compute_claim_fingerprint(
        subject_id="ent_alyssa_vance",
        predicate="FOUNDED",
        object_id="ent_cognitive_dyn",
        polarity="negated",
        temporal_scope="2022",
    )
    assert fp1 != fp_negated, "Opposite polarities must produce distinct claim fingerprints"


def test_evidence_quotation_validation_exact():
    """Verify exact character span validation against source document."""
    raw_text = "Dr. Alyssa Vance founded Cognitive Dynamics in late 2022."
    quote = "founded Cognitive Dynamics"
    start = raw_text.find(quote)
    end = start + len(quote)

    res = validate_evidence_quotation(raw_text, quote, start, end)
    assert res.is_valid is True
    assert "Exact character match confirmed" in res.reason


def test_evidence_quotation_validation_mismatch():
    """Verify offset and quotation mismatches are detected and rejected."""
    raw_text = "Dr. Alyssa Vance founded Cognitive Dynamics in late 2022."

    # Invalid offsets (out of bounds)
    res_oob = validate_evidence_quotation(raw_text, "founded", 100, 110)
    assert res_oob.is_valid is False

    # Quotation not present in text
    res_not_found = validate_evidence_quotation(raw_text, "nonexistent quote", 0, 10)
    assert res_not_found.is_valid is False


def test_quotation_disclaimer_preservation():
    """Verify the system explicitly records that quotation matching alone does not prove semantic claim correctness."""
    raw_text = "Dr. Marcus Chen founded Synapse Bio."
    quote = "founded Synapse Bio"
    start = raw_text.find(quote)
    end = start + len(quote)

    res = validate_evidence_quotation(raw_text, quote, start, end)
    d = res.to_dict()
    assert "disclaimer" in d
    assert "Quotation matching verifies text existence, not semantic claim correctness." in d["disclaimer"]


def test_duplicate_claim_aggregation(seeded_repository):
    """Verify that adding an identical claim aggregates evidence without creating duplicate nodes."""
    initial_claims_count = len(seeded_repository.list_claims())

    # Add duplicate claim for Vance founding Cognitive Dynamics
    cid = compute_claim_fingerprint(
        subject_id="ent_alyssa_vance",
        predicate="FOUNDED",
        object_id="ent_cognitive_dyn",
        polarity="affirmed",
        temporal_scope="2022",
    )
    duplicate_claim = Claim(
        id=cid,
        subject_id="ent_alyssa_vance",
        predicate="FOUNDED",
        object_id="ent_cognitive_dyn",
        polarity=Polarity.AFFIRMED,
        temporal_scope="2022",
        evidence_ids=["ev_extra_test_01"],
    )

    seeded_repository.add_claim(duplicate_claim)
    assert len(seeded_repository.list_claims()) == initial_claims_count

    merged = seeded_repository.get_claim(cid)
    assert "ev_extra_test_01" in merged.evidence_ids
