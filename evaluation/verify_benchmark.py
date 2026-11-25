"""NOESIS Validation Suite (NVS-100) Verification Script.

Validates:
1. Schema conformance of datasets/benchmarks/nvs100.json against datasets/benchmarks/schema.json.
2. Category count distributions (exact matching of all 9 categories).
3. Split breakdown (60 Dev / 40 Test).
4. Uniqueness of Case IDs and Questions.
5. Zero leakage: Paraphrased query split alignment with canonical query split.
6. Structured Query Plan integrity and ground truth format.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

BENCHMARK_PATH = Path(__file__).resolve().parent.parent / "datasets" / "benchmarks" / "nvs100.json"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "datasets" / "benchmarks" / "schema.json"

EXPECTED_CATEGORIES: Dict[str, Dict[str, int]] = {
    "single_hop": {"total": 15, "dev": 9, "test": 6},
    "two_hop": {"total": 15, "dev": 9, "test": 6},
    "three_hop": {"total": 15, "dev": 9, "test": 6},
    "multi_hop": {"total": 10, "dev": 6, "test": 4},
    "contradiction": {"total": 10, "dev": 6, "test": 4},
    "ablation": {"total": 10, "dev": 6, "test": 4},
    "unanswerable": {"total": 10, "dev": 6, "test": 4},
    "paraphrased": {"total": 10, "dev": 6, "test": 4},
    "adversarial": {"total": 5, "dev": 3, "test": 2},
}

TOTAL_EXPECTED_CASES = 100
TOTAL_DEV = 60
TOTAL_TEST = 40


def validate_schema_fallback(case: Dict[str, Any], idx: int) -> List[str]:
    """Fallback manual schema validation if jsonschema is not installed."""
    errors = []
    required_keys = [
        "case_id",
        "corpus_id",
        "category",
        "difficulty",
        "question",
        "structured_query_plan",
        "expected_answer_entities",
        "expected_reasoning_paths",
        "expected_predicates",
        "expected_directions",
        "expected_evidence",
        "expected_contradiction_status",
        "expected_abstention_status",
        "expected_critical_sources",
        "annotation_notes",
        "split",
    ]
    for key in required_keys:
        if key not in case:
            errors.append(f"Case #{idx} missing required key: '{key}'")

    if not re.match(r"^NVS-[0-9]{3}$", case.get("case_id", "")):
        errors.append(f"Case #{idx} invalid case_id pattern: {case.get('case_id')}")

    if case.get("category") not in EXPECTED_CATEGORIES:
        errors.append(f"Case #{idx} unknown category: {case.get('category')}")

    if case.get("difficulty") not in ["easy", "medium", "hard"]:
        errors.append(f"Case #{idx} unknown difficulty: {case.get('difficulty')}")

    if case.get("split") not in ["dev", "test"]:
        errors.append(f"Case #{idx} unknown split: {case.get('split')}")

    sqp = case.get("structured_query_plan")
    if not isinstance(sqp, dict):
        errors.append(f"Case #{idx} structured_query_plan must be an object")
    else:
        if "start_entity_id" not in sqp or "steps" not in sqp:
            errors.append(f"Case #{idx} structured_query_plan missing start_entity_id or steps")

    return errors


def verify_benchmark() -> bool:
    print(f"Loading benchmark from: {BENCHMARK_PATH}")
    if not BENCHMARK_PATH.exists():
        print(f"ERROR: Benchmark file not found at {BENCHMARK_PATH}")
        return False

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        cases: List[Dict[str, Any]] = json.load(f)

    print(f"Loaded {len(cases)} cases.")
    errors: List[str] = []

    # 1. Total Case Count
    if len(cases) != TOTAL_EXPECTED_CASES:
        errors.append(f"Expected exactly {TOTAL_EXPECTED_CASES} cases, got {len(cases)}")

    # 2. Schema Validation
    has_jsonschema = False
    try:
        import jsonschema

        with open(SCHEMA_PATH, "r", encoding="utf-8") as sf:
            schema = json.load(sf)
        has_jsonschema = True
    except ImportError:
        print("Note: jsonschema package not installed, using built-in schema validator.")

    case_map: Dict[str, Dict[str, Any]] = {}
    seen_questions: set[str] = set()

    for idx, case in enumerate(cases):
        cid = case.get("case_id", f"unknown_{idx}")
        if cid in case_map:
            errors.append(f"Duplicate case_id found: {cid}")
        case_map[cid] = case

        q = case.get("question", "").strip().lower()
        if q in seen_questions:
            errors.append(f"Duplicate question detected: '{case.get('question')}' (Case: {cid})")
        seen_questions.add(q)

        if has_jsonschema:
            try:
                jsonschema.validate(instance=case, schema=schema)
            except Exception as e:
                errors.append(f"Schema validation failed for {cid}: {str(e).splitlines()[0]}")
        else:
            fb_errors = validate_schema_fallback(case, idx)
            errors.extend(fb_errors)

    # 3. Category & Split Breakdown
    cat_counts = Counter(c["category"] for c in cases)
    split_counts = Counter(c["split"] for c in cases)

    if split_counts["dev"] != TOTAL_DEV or split_counts["test"] != TOTAL_TEST:
        errors.append(
            f"Split breakdown error: Expected {TOTAL_DEV} dev and {TOTAL_TEST} test, "
            f"got {split_counts['dev']} dev and {split_counts['test']} test"
        )

    for cat, expected in EXPECTED_CATEGORIES.items():
        actual_total = cat_counts[cat]
        if actual_total != expected["total"]:
            errors.append(f"Category '{cat}': expected {expected['total']} total, got {actual_total}")

        actual_dev = sum(1 for c in cases if c["category"] == cat and c["split"] == "dev")
        actual_test = sum(1 for c in cases if c["category"] == cat and c["split"] == "test")

        if actual_dev != expected["dev"] or actual_test != expected["test"]:
            errors.append(
                f"Category '{cat}' split mismatch: expected ({expected['dev']} dev, {expected['test']} test), "
                f"got ({actual_dev} dev, {actual_test} test)"
            )

    # 4. Paraphrase Split Alignment (Leakage Prevention)
    paraphrased_cases = [c for c in cases if c["category"] == "paraphrased"]
    for pc in paraphrased_cases:
        can_id = pc.get("canonical_query_id")
        if not can_id:
            errors.append(f"Paraphrased case {pc['case_id']} missing 'canonical_query_id'")
        elif can_id not in case_map:
            errors.append(f"Paraphrased case {pc['case_id']} references unknown canonical ID: {can_id}")
        else:
            canonical_case = case_map[can_id]
            if canonical_case["split"] != pc["split"]:
                errors.append(
                    f"Leakage violation: Paraphrased case {pc['case_id']} is '{pc['split']}' "
                    f"but its canonical case {can_id} is '{canonical_case['split']}'"
                )

    # Output verification results
    print("=" * 60)
    print("NVS-100 BENCHMARK VERIFICATION REPORT")
    print("=" * 60)
    print(f"Total Cases:     {len(cases)} / {TOTAL_EXPECTED_CASES}")
    print(f"Dev Split:       {split_counts['dev']} / {TOTAL_DEV}")
    print(f"Test Split:      {split_counts['test']} / {TOTAL_TEST}")
    print("-" * 60)
    print(f"{'Category':<16} {'Total':<8} {'Dev':<8} {'Test':<8} {'Status'}")
    print("-" * 60)
    for cat, exp in EXPECTED_CATEGORIES.items():
        act_tot = cat_counts[cat]
        act_dev = sum(1 for c in cases if c["category"] == cat and c["split"] == "dev")
        act_tst = sum(1 for c in cases if c["category"] == cat and c["split"] == "test")
        status = "OK" if (act_tot == exp["total"] and act_dev == exp["dev"] and act_tst == exp["test"]) else "FAIL"
        print(f"{cat:<16} {act_tot:<8} {act_dev:<8} {act_tst:<8} {status}")
    print("=" * 60)

    if errors:
        print(f"\nVERIFICATION FAILED: {len(errors)} error(s) found:")
        for err in errors:
            print(f" - {err}")
        return False

    print("\nALL VERIFICATION CHECKS PASSED SUCCESSFULLY (Zero Leakage Confirmed).")
    return True


if __name__ == "__main__":
    success = verify_benchmark()
    sys.exit(0 if success else 1)
