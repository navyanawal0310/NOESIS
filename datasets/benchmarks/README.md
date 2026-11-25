# NOESIS Validation Suite (NVS-100) Benchmark

## Overview

The **NOESIS Validation Suite (NVS-100)** is a curated, deterministic gold-standard evaluation benchmark designed to measure multi-hop reasoning, evidence provenance attribution, contradiction handling, ablation sensitivity, knowledge gap abstention, and robustness against adversarial prompts.

It covers **100 rigorously constructed benchmark cases** mapped directly against the 15-document synthetic corpus (`DOC_001` to `DOC_015`) and evaluated across both structured query execution and natural-language query compilation.

---

## Category Distribution (Total: 100 Cases)

| Category | Count | Dev (60%) | Test (40%) | Primary Research Objective |
| :--- | :---: | :---: | :---: | :--- |
| **`single_hop`** | 15 | 9 | 6 | Baseline entity-to-entity verification & citation fidelity |
| **`two_hop`** | 15 | 9 | 6 | Intermediate node bridging & predicate directionality |
| **`three_hop`** | 15 | 9 | 6 | Target three-hop scientific inference across disjoint documents |
| **`multi_hop`** | 10 | 6 | 4 | Extended chains (4-hop and 5-hop reasoning paths) |
| **`contradiction`** | 10 | 6 | 4 | Polar claim identification and dialectical tension reporting |
| **`ablation`** | 10 | 6 | 4 | Non-destructive counterfactual source pruning & path collapse |
| **`unanswerable`** | 10 | 6 | 4 | Knowledge gap detection & rigorous abstention |
| **`paraphrased`** | 10 | 6 | 4 | Lexical invariance under syntactic and semantic variation |
| **`adversarial`** | 5 | 3 | 2 | Resistance to prompt injection, false premises & hallucination traps |
| **Total** | **100** | **60** | **40** | **Comprehensive Evaluation** |

---

## Benchmark Schema

Every benchmark case adheres strictly to `datasets/benchmarks/schema.json` and contains:
- `case_id`: Identifier formatted as `^NVS-[0-9]{3}$` (`NVS-001` through `NVS-100`).
- `corpus_id`: Target corpus version (e.g., `synthetic_v1_15docs`).
- `category`: One of the 9 defined categories.
- `difficulty`: `easy`, `medium`, or `hard`.
- `question`: Natural-language research query.
- `structured_query_plan`: Canonical `StructuredQueryPlan` (start entity, step predicates, directions, target types).
- `expected_answer_entities`: List of canonical target entity IDs.
- `expected_reasoning_paths`: List of valid ordered node-edge-node entity/claim path sequences.
- `expected_predicates`: Exact sequence of relational predicates expected.
- `expected_directions`: Exact sequence of directions (`incoming` or `outgoing`).
- `expected_evidence`: List of exact quotation strings supporting the inference.
- `expected_contradiction_status`: Boolean indicator of whether a contradiction is present.
- `expected_abstention_status`: Boolean indicator of whether abstention is the correct response.
- `expected_critical_sources`: Specific document IDs whose ablation destroys the reasoning path.
- `canonical_query_id`: Identifier of canonical parent query (for `paraphrased` cases).
- `annotation_notes`: Ground truth justification and notes.
- `split`: `dev` or `test`.

---

## Split Protocol & Leakage Prevention

1. **Partition Ratio**: 60% Development (`dev`), 40% Held-Out Test (`test`).
2. **Deterministic Assignment**: Cases are systematically split within each category to ensure balanced difficulty and topology representation.
3. **Paraphrase Constraint**: All paraphrased queries (`NVS-086` to `NVS-095`) strictly inherit the partition split of their corresponding canonical query to prevent dev-to-test semantic contamination.
4. **Development vs. Evaluation Protocol**:
   - Prompt engineering, EAQC rule tuning, and cache warmups are permitted only on `dev`.
   - Final comparative benchmark reports (NOESIS vs. Baselines) are computed and published on `test`.

---

## Verification

To verify schema conformance, case integrity, and partition consistency:
```powershell
python evaluation/verify_benchmark.py
```
