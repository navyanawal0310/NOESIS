"""Ground Truth Dataset and Benchmark Query Specifications for NOESIS."""

import json
from pathlib import Path
from datasets.synthetic.builder import build_corpus_data

corpus = build_corpus_data()

GROUND_TRUTH_QUERIES = [
    {
        "id": "Q_3HOP_PROMETHEUS_TECH",
        "description": "Three-hop reasoning connecting project researchers to technologies",
        "question": "Which technologies were developed by organizations founded by researchers who worked on Project Prometheus?",
        "query_plan": {
            "start_entity": "ent_proj_prometheus",
            "steps": [
                {"predicate": "WORKED_ON", "direction": "incoming"},
                {"predicate": "FOUNDED", "direction": "outgoing"},
                {"predicate": "DEVELOPED", "direction": "outgoing"},
            ],
            "return_type": "TECHNOLOGY",
            "max_hops": 3,
        },
        "expected_matches": ["ent_tech_axiom_reasoner", "ent_tech_synaptic_core"],
        "expected_hops": 3,
        "critical_source_for_match": {
            "ent_tech_synaptic_core": "DOC_003",
        },
        "redundant_sources_for_match": {
            "ent_tech_axiom_reasoner": ["DOC_001", "DOC_006"],
        },
    },
    {
        "id": "Q_2HOP_NEXUS_RESEARCHERS",
        "description": "Two-hop reasoning finding researchers on funded projects",
        "question": "Which researchers worked on projects funded by Nexus Advanced Research Institute?",
        "query_plan": {
            "start_entity": "ent_nexus_institute",
            "steps": [
                {"predicate": "FUNDED", "direction": "outgoing"},
                {"predicate": "WORKED_ON", "direction": "incoming"},
            ],
            "return_type": "PERSON",
            "max_hops": 2,
        },
        "expected_matches": ["ent_alyssa_vance", "ent_marcus_chen", "ent_elena_rostova"],
        "expected_hops": 2,
    },
    {
        "id": "Q_1HOP_ZURICH_ORGS",
        "description": "Single-hop incoming location query",
        "question": "Which organizations are located in Zurich Innovation Center?",
        "query_plan": {
            "start_entity": "ent_zurich",
            "steps": [
                {"predicate": "LOCATED_IN", "direction": "incoming"},
            ],
            "return_type": "ORGANIZATION",
            "max_hops": 1,
        },
        "expected_matches": ["ent_cognitive_dyn", "ent_helix_foundry", "ent_qubit_dynamics"],
        "expected_hops": 1,
    },
    {
        "id": "Q_UNANSWERABLE_HYPERION_QUANTUM",
        "description": "Negative control: query with missing relationship requiring insufficient evidence response",
        "question": "Which quantum protocols were developed by organizations that employed researchers who worked on Project Hyperion?",
        "query_plan": {
            "start_entity": "ent_proj_hyperion",
            "steps": [
                {"predicate": "WORKED_ON", "direction": "incoming"},
                {"predicate": "EMPLOYED_BY", "direction": "outgoing"},
                {"predicate": "DEVELOPED", "direction": "outgoing"},
            ],
            "return_type": "TECHNOLOGY",
            "predicate_filter": "DEVELOPED_QUANTUM",
            "max_hops": 3,
        },
        "expected_matches": [],
        "expected_status": "insufficient_evidence",
    },
]

benchmark_payload = {
    "corpus": corpus,
    "queries": GROUND_TRUTH_QUERIES,
    "metadata": {
        "version": "1.0.0",
        "domain": "Artificial Intelligence & Computational Systems",
        "total_documents": len(corpus["documents"]),
        "total_entities": len(corpus["entities"]),
        "total_claims": len(corpus["claims"]),
        "total_evidence": len(corpus["evidence"]),
        "total_contradictions": len(corpus["contradictions"]),
    },
}

out_dir = Path("datasets/ground_truth")
out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / "ground_truth.json", "w", encoding="utf-8") as f:
    json.dump(benchmark_payload, f, indent=2)

print("Saved datasets/ground_truth/ground_truth.json successfully!")
