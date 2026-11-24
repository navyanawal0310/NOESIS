"""Builder and Validator for Synthetic Corpus Fixtures."""

import json
from pathlib import Path
from typing import Any, Dict, List
from backend.app.extraction.fingerprint import compute_claim_fingerprint
from backend.app.extraction.validator import validate_evidence_quotation
from datasets.synthetic.corpus import SYNTHETIC_DOCUMENTS

# 28 Canonical Entities
ENTITIES_DATA = [
    {"id": "ent_alyssa_vance", "canonical_name": "Dr. Alyssa Vance", "type": "PERSON", "aliases": ["Alyssa Vance", "A. Vance"], "description": "Principal investigator of Project Prometheus"},
    {"id": "ent_marcus_chen", "canonical_name": "Dr. Marcus Chen", "type": "PERSON", "aliases": ["Marcus Chen", "M. Chen"], "description": "Senior systems architect and founder of Synapse Bio"},
    {"id": "ent_elena_rostova", "canonical_name": "Dr. Elena Rostova", "type": "PERSON", "aliases": ["Elena Rostova", "E. Rostova"], "description": "Chief verification architect of Neural Mesh"},
    {"id": "ent_tariq_al_mansoor", "canonical_name": "Dr. Tariq Al-Mansoor", "type": "PERSON", "aliases": ["Tariq Al-Mansoor"], "description": "Principal quantum engineer at Qubit Dynamics"},
    {"id": "ent_sarah_jenkins", "canonical_name": "Dr. Sarah Jenkins", "type": "PERSON", "aliases": ["Sarah Jenkins"], "description": "Research director at DeepLogic Labs"},
    {"id": "ent_vikram_patel", "canonical_name": "Dr. Vikram Patel", "type": "PERSON", "aliases": ["Vikram Patel"], "description": "Research fellow at Turing Institute of Bengaluru"},
    {"id": "ent_clara_weber", "canonical_name": "Dr. Clara Weber", "type": "PERSON", "aliases": ["Clara Weber"], "description": "Executive board member at Cognitive Dynamics"},
    {"id": "ent_daniel_kim", "canonical_name": "Dr. Daniel Kim", "type": "PERSON", "aliases": ["Daniel Kim"], "description": "Chief scientist at Apex Robotics"},

    {"id": "ent_nexus_institute", "canonical_name": "Nexus Advanced Research Institute", "type": "ORGANIZATION", "aliases": ["Nexus Institute"], "description": "Multi-institutional research facility"},
    {"id": "ent_synapse_bio", "canonical_name": "Synapse Bio", "type": "ORGANIZATION", "aliases": ["Synapse Bio Technologies"], "description": "Neuromorphic biotechnology enterprise"},
    {"id": "ent_deep_logic", "canonical_name": "DeepLogic Labs", "type": "ORGANIZATION", "aliases": ["DeepLogic"], "description": "Event-driven AI research lab"},
    {"id": "ent_cognitive_dyn", "canonical_name": "Cognitive Dynamics", "type": "ORGANIZATION", "aliases": ["Cognitive Dynamics Corporation"], "description": "Neuro-symbolic reasoning commercial venture"},
    {"id": "ent_qubit_dynamics", "canonical_name": "Qubit Dynamics Group", "type": "ORGANIZATION", "aliases": ["Qubit Dynamics"], "description": "Solid-state quantum technology consortium"},
    {"id": "ent_turing_bengaluru", "canonical_name": "Turing Institute of Bengaluru", "type": "ORGANIZATION", "aliases": ["Turing Bengaluru"], "description": "Indian AI research institute"},
    {"id": "ent_apex_robotics", "canonical_name": "Apex Robotics Systems", "type": "ORGANIZATION", "aliases": ["Apex Robotics"], "description": "Autonomous robotics research lab"},
    {"id": "ent_helix_foundry", "canonical_name": "Helix Compute Foundry", "type": "ORGANIZATION", "aliases": ["Helix Foundry"], "description": "Custom silicon fabrication foundry"},

    {"id": "ent_proj_prometheus", "canonical_name": "Project Prometheus", "type": "PROJECT", "aliases": ["Prometheus Project"], "description": "Self-supervised neural reasoning initiative"},
    {"id": "ent_proj_aegis", "canonical_name": "Project Aegis", "type": "PROJECT", "aliases": ["Aegis Project"], "description": "Adversarial vulnerability research project"},
    {"id": "ent_proj_chronos", "canonical_name": "Project Chronos", "type": "PROJECT", "aliases": ["Chronos Project"], "description": "Continuous-time temporal reasoning initiative"},
    {"id": "ent_proj_hyperion", "canonical_name": "Project Hyperion", "type": "PROJECT", "aliases": ["Hyperion Project"], "description": "Decentralized autonomous AI governance protocol"},

    {"id": "ent_tech_neural_mesh", "canonical_name": "Neural Mesh v2", "type": "TECHNOLOGY", "aliases": ["Neural Mesh"], "description": "Adversarially robust graph topology"},
    {"id": "ent_tech_synaptic_core", "canonical_name": "Synaptic Core Engine", "type": "TECHNOLOGY", "aliases": ["Synaptic Core"], "description": "Neuromorphic spike recognition co-processor"},
    {"id": "ent_tech_tensor_stream", "canonical_name": "TensorStream Runtime", "type": "TECHNOLOGY", "aliases": ["TensorStream"], "description": "Asynchronous tensor execution pipeline"},
    {"id": "ent_tech_qubit_sync", "canonical_name": "QubitSync Protocol", "type": "TECHNOLOGY", "aliases": ["QubitSync"], "description": "Quantum-classical pulse synchronization protocol"},
    {"id": "ent_tech_axiom_reasoner", "canonical_name": "Axiom Semantic Reasoner", "type": "TECHNOLOGY", "aliases": ["Axiom Reasoner"], "description": "Ontological verification inference engine"},
    {"id": "ent_tech_holo_vector", "canonical_name": "HoloVector Architecture", "type": "TECHNOLOGY", "aliases": ["HoloVector"], "description": "Spatial multi-robot localization architecture"},

    {"id": "ent_bengaluru", "canonical_name": "Bengaluru Tech Corridor", "type": "LOCATION", "aliases": ["Bengaluru"], "description": "Technology innovation district in Karnataka"},
    {"id": "ent_zurich", "canonical_name": "Zurich Innovation Center", "type": "LOCATION", "aliases": ["Zurich"], "description": "Technology cluster in Switzerland"},
]

RAW_CLAIMS_EVIDENCE = [
    # DOC_001
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_alyssa_vance",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_prometheus",
        "polarity": "affirmed",
        "temporal_scope": "2021-2022",
        "quote": "Dr. Alyssa Vance served as the principal investigator and lead researcher who worked on Project Prometheus during its formative stages.",
        "page": 1,
    },
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_alyssa_vance",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_nexus_institute",
        "polarity": "affirmed",
        "temporal_scope": "2020-2022",
        "quote": "Historical records state that Dr. Alyssa Vance was employed by Nexus Advanced Research Institute prior to her commercial spinout.",
        "page": 1,
    },
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_alyssa_vance",
        "predicate": "FOUNDED",
        "object_id": "ent_cognitive_dyn",
        "polarity": "affirmed",
        "temporal_scope": "2022",
        "quote": "Dr. Alyssa Vance founded Cognitive Dynamics in late 2022 to commercialize neuro-symbolic reasoning systems.",
        "page": 1,
    },
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_axiom_reasoner",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Cognitive Dynamics developed the Axiom Semantic Reasoner, a specialized inference engine designed for formal mathematical and ontological verification.",
        "page": 1,
    },
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_nexus_institute",
        "predicate": "FOUNDED",
        "object_id": "ent_proj_prometheus",
        "polarity": "affirmed",
        "temporal_scope": "2021",
        "quote": "In early 2021, the Nexus Advanced Research Institute launched Project Prometheus, an ambitious multi-institutional research initiative",
        "page": 1,
    },
    {
        "doc_id": "DOC_001",
        "subject_id": "ent_nexus_institute",
        "predicate": "FUNDED",
        "object_id": "ent_proj_prometheus",
        "polarity": "affirmed",
        "temporal_scope": "2021",
        "quote": "Nexus Advanced Research Institute funded Project Prometheus with initial exploratory grants.",
        "page": 1,
    },

    # DOC_002
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "LOCATED_IN",
        "object_id": "ent_zurich",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "Cognitive Dynamics is located in Zurich Innovation Center, where it maintains its primary engineering facility.",
        "page": 1,
    },
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_axiom_reasoner",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Cognitive Dynamics developed the Axiom Semantic Reasoner for high-assurance industries.",
        "page": 1,
    },
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_clara_weber",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_cognitive_dyn",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "Dr. Clara Weber joined the executive board and was employed by Cognitive Dynamics as strategy director.",
        "page": 1,
    },
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_clara_weber",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_alyssa_vance",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "Records show Dr. Clara Weber collaborated with Dr. Alyssa Vance on multi-agent consensus protocols.",
        "page": 1,
    },
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "USES",
        "object_id": "ent_tech_tensor_stream",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "The organization actively uses TensorStream Runtime to accelerate inference pipelines.",
        "page": 1,
    },
    {
        "doc_id": "DOC_002",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "USES",
        "object_id": "ent_tech_axiom_reasoner",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Cognitive Dynamics uses Axiom Semantic Reasoner for customer data integrity.",
        "page": 1,
    },

    # DOC_003 (CRITICAL SOURCE FOR MARCUS CHEN -> SYNAPSE BIO)
    {
        "doc_id": "DOC_003",
        "subject_id": "ent_marcus_chen",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_prometheus",
        "polarity": "affirmed",
        "temporal_scope": "2021-2022",
        "quote": "Dr. Marcus Chen worked on Project Prometheus as senior systems architect until 2022.",
        "page": 1,
    },
    {
        "doc_id": "DOC_003",
        "subject_id": "ent_marcus_chen",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_nexus_institute",
        "polarity": "affirmed",
        "temporal_scope": "2021-2022",
        "quote": "Archival employment logs verify that Dr. Marcus Chen was employed by Nexus Advanced Research Institute during this period.",
        "page": 1,
    },
    {
        "doc_id": "DOC_003",
        "subject_id": "ent_marcus_chen",
        "predicate": "FOUNDED",
        "object_id": "ent_synapse_bio",
        "polarity": "affirmed",
        "temporal_scope": "2022",
        "quote": "Dr. Marcus Chen founded Synapse Bio.",
        "page": 1,
    },
    {
        "doc_id": "DOC_003",
        "subject_id": "ent_synapse_bio",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_synaptic_core",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Synapse Bio developed the Synaptic Core Engine, a neuromorphic co-processor capable of real-time spike pattern recognition.",
        "page": 1,
    },
    {
        "doc_id": "DOC_003",
        "subject_id": "ent_synapse_bio",
        "predicate": "USES",
        "object_id": "ent_tech_tensor_stream",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Synapse Bio uses TensorStream Runtime for pipeline acceleration.",
        "page": 1,
    },

    # DOC_004
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_sarah_jenkins",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_deep_logic",
        "polarity": "affirmed",
        "temporal_scope": "2019-2023",
        "quote": "Dr. Sarah Jenkins was employed by DeepLogic Labs as research director from 2019 to 2023.",
        "page": 1,
    },
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_sarah_jenkins",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_chronos",
        "polarity": "affirmed",
        "temporal_scope": "2020-2022",
        "quote": "Dr. Sarah Jenkins worked on Project Chronos, an effort aimed at continuous-time temporal reasoning.",
        "page": 1,
    },
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_deep_logic",
        "predicate": "FUNDED",
        "object_id": "ent_proj_chronos",
        "polarity": "affirmed",
        "temporal_scope": "2020-2023",
        "quote": "DeepLogic Labs funded Project Chronos through multi-year allocations.",
        "page": 1,
    },
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_deep_logic",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_tensor_stream",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "DeepLogic Labs developed the TensorStream Runtime to support high-throughput asynchronous execution.",
        "page": 1,
    },
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_deep_logic",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_helix_foundry",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "The lab maintained active collaborations with Helix Compute Foundry for specialized silicon tape-outs.",
        "page": 1,
    },
    {
        "doc_id": "DOC_004",
        "subject_id": "ent_helix_foundry",
        "predicate": "LOCATED_IN",
        "object_id": "ent_zurich",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Helix Compute Foundry is located in Zurich Innovation Center adjacent to the microelectronics cluster.",
        "page": 1,
    },

    # DOC_005
    {
        "doc_id": "DOC_005",
        "subject_id": "ent_elena_rostova",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_aegis",
        "polarity": "affirmed",
        "temporal_scope": "2021-2023",
        "quote": "Dr. Elena Rostova worked on Project Aegis as chief verification architect.",
        "page": 1,
    },
    {
        "doc_id": "DOC_005",
        "subject_id": "ent_elena_rostova",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_nexus_institute",
        "polarity": "affirmed",
        "temporal_scope": "2021-2023",
        "quote": "Personnel rosters state Dr. Elena Rostova was employed by Nexus Advanced Research Institute during the core research phase.",
        "page": 1,
    },
    {
        "doc_id": "DOC_005",
        "subject_id": "ent_elena_rostova",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_neural_mesh",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Dr. Elena Rostova developed Neural Mesh v2, a topology designed to resist gradient-based adversarial perturbations.",
        "page": 1,
    },
    {
        "doc_id": "DOC_005",
        "subject_id": "ent_nexus_institute",
        "predicate": "FUNDED",
        "object_id": "ent_proj_aegis",
        "polarity": "affirmed",
        "temporal_scope": "2021-2024",
        "quote": "Nexus Advanced Research Institute funded Project Aegis with foundational grants between 2021 and 2024.",
        "page": 1,
    },
    {
        "doc_id": "DOC_005",
        "subject_id": "ent_proj_aegis",
        "predicate": "USES",
        "object_id": "ent_tech_neural_mesh",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Project Aegis uses Neural Mesh v2 as its primary benchmarking testbed.",
        "page": 1,
    },

    # DOC_006 (REPEATED EVIDENCE)
    {
        "doc_id": "DOC_006",
        "subject_id": "ent_alyssa_vance",
        "predicate": "FOUNDED",
        "object_id": "ent_cognitive_dyn",
        "polarity": "affirmed",
        "temporal_scope": "2022",
        "quote": "Historical corporate filings confirm that Dr. Alyssa Vance founded Cognitive Dynamics after departing academia.",
        "page": 1,
    },
    {
        "doc_id": "DOC_006",
        "subject_id": "ent_alyssa_vance",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_prometheus",
        "polarity": "affirmed",
        "temporal_scope": "2021-2022",
        "quote": "The biographical entry corroborates that Dr. Alyssa Vance worked on Project Prometheus between 2021 and 2022.",
        "page": 1,
    },
    {
        "doc_id": "DOC_006",
        "subject_id": "ent_alyssa_vance",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_clara_weber",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "Dr. Alyssa Vance collaborated with Dr. Clara Weber to formalize decentralized agent consensus.",
        "page": 1,
    },

    # DOC_007 (CONTRADICTION: Vance did NOT found Cognitive Dynamics)
    {
        "doc_id": "DOC_007",
        "subject_id": "ent_alyssa_vance",
        "predicate": "FOUNDED",
        "object_id": "ent_cognitive_dyn",
        "polarity": "negated",
        "temporal_scope": "2022",
        "quote": "According to internal governance memorandums, Dr. Alyssa Vance did not found Cognitive Dynamics, having acted solely as an external scientific consultant",
        "page": 1,
    },

    # DOC_008 (CONTRADICTION: Location in Bengaluru vs Zurich)
    {
        "doc_id": "DOC_008",
        "subject_id": "ent_cognitive_dyn",
        "predicate": "LOCATED_IN",
        "object_id": "ent_bengaluru",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "commercial licensing indicates that Cognitive Dynamics is located in Bengaluru Tech Corridor under a foreign direct investment initiative.",
        "page": 1,
    },
    {
        "doc_id": "DOC_008",
        "subject_id": "ent_turing_bengaluru",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_vikram_patel",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Turing Institute of Bengaluru collaborated with Dr. Vikram Patel on local incubation.",
        "page": 1,
    },
    {
        "doc_id": "DOC_008",
        "subject_id": "ent_vikram_patel",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_turing_bengaluru",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Dr. Vikram Patel was employed by Turing Institute of Bengaluru to direct machine intelligence workshops.",
        "page": 1,
    },
    {
        "doc_id": "DOC_008",
        "subject_id": "ent_turing_bengaluru",
        "predicate": "LOCATED_IN",
        "object_id": "ent_bengaluru",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Turing Institute of Bengaluru is located in Bengaluru Tech Corridor within the electronic city precinct.",
        "page": 1,
    },

    # DOC_009
    {
        "doc_id": "DOC_009",
        "subject_id": "ent_tariq_al_mansoor",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_qubit_dynamics",
        "polarity": "affirmed",
        "temporal_scope": "2021-2023",
        "quote": "Dr. Tariq Al-Mansoor was employed by Qubit Dynamics Group as principal quantum engineer.",
        "page": 1,
    },
    {
        "doc_id": "DOC_009",
        "subject_id": "ent_qubit_dynamics",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_qubit_sync",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Qubit Dynamics Group developed the QubitSync Protocol to synchronize pulse channels.",
        "page": 1,
    },
    {
        "doc_id": "DOC_009",
        "subject_id": "ent_tariq_al_mansoor",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_elena_rostova",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Dr. Tariq Al-Mansoor collaborated with Dr. Elena Rostova on quantum error-correcting neural topographies.",
        "page": 1,
    },
    {
        "doc_id": "DOC_009",
        "subject_id": "ent_qubit_dynamics",
        "predicate": "LOCATED_IN",
        "object_id": "ent_zurich",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Qubit Dynamics Group is located in Zurich Innovation Center near partner physics laboratories.",
        "page": 1,
    },
    {
        "doc_id": "DOC_009",
        "subject_id": "ent_qubit_dynamics",
        "predicate": "USES",
        "object_id": "ent_tech_qubit_sync",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Qubit Dynamics Group uses QubitSync Protocol for real-time calibration.",
        "page": 1,
    },

    # DOC_010 (BOUNDED NEGATIVE TEST CASE)
    {
        "doc_id": "DOC_010",
        "subject_id": "ent_daniel_kim",
        "predicate": "WORKED_ON",
        "object_id": "ent_proj_hyperion",
        "polarity": "affirmed",
        "temporal_scope": "2023",
        "quote": "Dr. Daniel Kim worked on Project Hyperion from its inception in mid-2023.",
        "page": 1,
    },
    {
        "doc_id": "DOC_010",
        "subject_id": "ent_daniel_kim",
        "predicate": "EMPLOYED_BY",
        "object_id": "ent_apex_robotics",
        "polarity": "affirmed",
        "temporal_scope": "2023-2024",
        "quote": "Dr. Daniel Kim was employed by Apex Robotics Systems to direct autonomous fleet coordination.",
        "page": 1,
    },
    {
        "doc_id": "DOC_010",
        "subject_id": "ent_apex_robotics",
        "predicate": "DEVELOPED",
        "object_id": "ent_tech_holo_vector",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Apex Robotics Systems developed the HoloVector Architecture for spatial multi-robot localization.",
        "page": 1,
    },
    {
        "doc_id": "DOC_010",
        "subject_id": "ent_apex_robotics",
        "predicate": "LOCATED_IN",
        "object_id": "ent_bengaluru",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Apex Robotics Systems is located in Bengaluru Tech Corridor near industrial robotics facilities.",
        "page": 1,
    },
    {
        "doc_id": "DOC_010",
        "subject_id": "ent_daniel_kim",
        "predicate": "COLLABORATED_WITH",
        "object_id": "ent_vikram_patel",
        "polarity": "affirmed",
        "temporal_scope": None,
        "quote": "Dr. Daniel Kim collaborated with Dr. Vikram Patel on distributed localization benchmarks.",
        "page": 1,
    },
]


def build_corpus_data():
    """Validates and compiles all documents, entities, claims, and evidence."""
    doc_map = {d["id"]: d for d in SYNTHETIC_DOCUMENTS}

    compiled_claims = {}
    compiled_evidence = []
    contradiction_pairs = []

    for idx, item in enumerate(RAW_CLAIMS_EVIDENCE):
        doc = doc_map.get(item["doc_id"])
        if not doc:
            raise ValueError(f"Document {item['doc_id']} not found!")

        raw_text = doc["raw_text"]
        quote = item["quote"]

        start_offset = raw_text.find(quote)
        if start_offset == -1:
            raise ValueError(f"Quotation '{quote}' not found in document {item['doc_id']}!")
        end_offset = start_offset + len(quote)

        # Validate quotation
        v_res = validate_evidence_quotation(raw_text, quote, start_offset, end_offset)
        if not v_res.is_valid:
            raise ValueError(f"Validation failed for quote: {v_res.reason}")

        # Deterministic claim fingerprint
        claim_id = compute_claim_fingerprint(
            subject_id=item["subject_id"],
            predicate=item["predicate"],
            object_id=item["object_id"],
            polarity=item["polarity"],
            temporal_scope=item["temporal_scope"],
        )

        ev_id = f"ev_{item['doc_id'].lower()}_{idx + 1:02d}"

        if claim_id not in compiled_claims:
            compiled_claims[claim_id] = {
                "id": claim_id,
                "subject_id": item["subject_id"],
                "predicate": item["predicate"],
                "object_id": item["object_id"],
                "polarity": item["polarity"],
                "temporal_scope": item["temporal_scope"],
                "confidence": 1.0,
                "evidence_ids": [ev_id],
                "contradiction_ids": [],
            }
        else:
            compiled_claims[claim_id]["evidence_ids"].append(ev_id)

        compiled_evidence.append({
            "id": ev_id,
            "claim_id": claim_id,
            "document_id": item["doc_id"],
            "quote": quote,
            "page": item["page"],
            "chunk_id": f"chk_{item['doc_id']}_01",
            "char_offset_start": start_offset,
            "char_offset_end": end_offset,
            "confidence": 1.0,
        })

    # Detect contradictions
    claim_list = list(compiled_claims.values())
    for i in range(len(claim_list)):
        for j in range(i + 1, len(claim_list)):
            c1 = claim_list[i]
            c2 = claim_list[j]

            # Case 1: Same subject & predicate & object, opposite polarity
            if (
                c1["subject_id"] == c2["subject_id"]
                and c1["predicate"] == c2["predicate"]
                and c1["object_id"] == c2["object_id"]
                and c1["polarity"] != c2["polarity"]
            ):
                contradiction_pairs.append((c1["id"], c2["id"]))
                c1["contradiction_ids"].append(c2["id"])
                c2["contradiction_ids"].append(c1["id"])

            # Case 2: LOCATED_IN single-valued attribute contradiction
            elif (
                c1["subject_id"] == c2["subject_id"]
                and c1["predicate"] == "LOCATED_IN"
                and c2["predicate"] == "LOCATED_IN"
                and c1["object_id"] != c2["object_id"]
            ):
                contradiction_pairs.append((c1["id"], c2["id"]))
                c1["contradiction_ids"].append(c2["id"])
                c2["contradiction_ids"].append(c1["id"])

    return {
        "documents": SYNTHETIC_DOCUMENTS,
        "entities": ENTITIES_DATA,
        "claims": list(compiled_claims.values()),
        "evidence": compiled_evidence,
        "contradictions": contradiction_pairs,
    }


if __name__ == "__main__":
    data = build_corpus_data()
    print(f"Entities: {len(data['entities'])}")
    print(f"Unique Claims: {len(data['claims'])}")
    print(f"Evidence Records: {len(data['evidence'])}")
    print(f"Contradiction Pairs: {len(data['contradictions'])}")
