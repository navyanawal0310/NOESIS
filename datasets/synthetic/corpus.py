"""Synthetic Research Corpus Data for NOESIS.

This dataset is strictly synthetic and generated for evaluating knowledge graph reasoning,
multi-hop traversal, contradiction detection, and counterfactual evidence ablation.
"""

from typing import Any, Dict, List

SYNTHETIC_DOCUMENTS: List[Dict[str, Any]] = [
    {
        "id": "DOC_001",
        "title": "Foundations of Project Prometheus and Cognitive Dynamics",
        "source_type": "synthetic",
        "publication_date": "2023-01-15",
        "source_uri": "synthetic://corpus/doc_001.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "In early 2021, the Nexus Advanced Research Institute launched Project Prometheus, "
            "an ambitious multi-institutional research initiative focused on self-supervised "
            "neural representation learning. Dr. Alyssa Vance served as the principal investigator "
            "and lead researcher who worked on Project Prometheus during its formative stages. "
            "Historical records state that Dr. Alyssa Vance was employed by Nexus Advanced Research Institute "
            "prior to her commercial spinout. "
            "Following breakthrough results in graph-structured attention, Dr. Alyssa Vance founded "
            "Cognitive Dynamics in late 2022 to commercialize neuro-symbolic reasoning systems. "
            "Under her technical guidance, Cognitive Dynamics developed the Axiom Semantic Reasoner, "
            "a specialized inference engine designed for formal mathematical and ontological verification. "
            "Nexus Advanced Research Institute funded Project Prometheus with initial exploratory grants."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_research_report"},
    },
    {
        "id": "DOC_002",
        "title": "Annual Technical Review of Cognitive Dynamics Corporation",
        "source_type": "synthetic",
        "publication_date": "2023-08-20",
        "source_uri": "synthetic://corpus/doc_002.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "The 2023 technical audit of Cognitive Dynamics Corporation highlights key structural developments. "
            "Cognitive Dynamics is located in Zurich Innovation Center, where it maintains its primary engineering facility. "
            "The company confirmed that Cognitive Dynamics developed the Axiom Semantic Reasoner for high-assurance industries. "
            "Furthermore, Dr. Clara Weber joined the executive board and was employed by Cognitive Dynamics as strategy director. "
            "Records show Dr. Clara Weber collaborated with Dr. Alyssa Vance on multi-agent consensus protocols. "
            "The organization actively uses TensorStream Runtime to accelerate inference pipelines. "
            "In production testing, Cognitive Dynamics uses Axiom Semantic Reasoner for customer data integrity."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_audit"},
    },
    {
        "id": "DOC_003",
        "title": "The Genesis of Synapse Bio Technologies and Synaptic Core",
        "source_type": "synthetic",
        "publication_date": "2023-03-10",
        "source_uri": "synthetic://corpus/doc_003.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "CRITICAL PROVENANCE RECORD: Dr. Marcus Chen worked on Project Prometheus as senior systems architect until 2022. "
            "Archival employment logs verify that Dr. Marcus Chen was employed by Nexus Advanced Research Institute during this period. "
            "Seeking to apply distributed neural architectures to biological signal processing, Dr. Marcus Chen founded Synapse Bio. "
            "Operating in close partnership with academic medical centers, Synapse Bio developed the Synaptic Core Engine, "
            "a neuromorphic co-processor capable of real-time spike pattern recognition. "
            "In its production laboratory, Synapse Bio uses TensorStream Runtime for pipeline acceleration. "
            "Note: This document provides the single primary attribution connecting Dr. Chen to the founding of Synapse Bio."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_biography", "is_critical_ablation_source": True},
    },
    {
        "id": "DOC_004",
        "title": "DeepLogic Labs and the Chronos Neuromorphic Project",
        "source_type": "synthetic",
        "publication_date": "2022-11-05",
        "source_uri": "synthetic://corpus/doc_004.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "DeepLogic Labs has accelerated its investment in event-driven artificial intelligence. "
            "Dr. Sarah Jenkins was employed by DeepLogic Labs as research director from 2019 to 2023. "
            "During her tenure, Dr. Sarah Jenkins worked on Project Chronos, an effort aimed at continuous-time temporal reasoning. "
            "Corporate archives confirm that DeepLogic Labs funded Project Chronos through multi-year allocations. "
            "DeepLogic Labs developed the TensorStream Runtime to support high-throughput asynchronous execution. "
            "The lab maintained active collaborations with Helix Compute Foundry for specialized silicon tape-outs. "
            "Helix Compute Foundry is located in Zurich Innovation Center adjacent to the microelectronics cluster."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_industry_brief"},
    },
    {
        "id": "DOC_005",
        "title": "Project Aegis and the Evolution of Neural Mesh v2",
        "source_type": "synthetic",
        "publication_date": "2023-05-18",
        "source_uri": "synthetic://corpus/doc_005.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "Project Aegis was instituted to establish mathematical bounds on neural network adversarial vulnerability. "
            "Dr. Elena Rostova worked on Project Aegis as chief verification architect. "
            "Personnel rosters state Dr. Elena Rostova was employed by Nexus Advanced Research Institute during the core research phase. "
            "In collaboration with partner laboratories, Dr. Elena Rostova developed Neural Mesh v2, "
            "a topology designed to resist gradient-based adversarial perturbations. "
            "Nexus Advanced Research Institute funded Project Aegis with foundational grants between 2021 and 2024. "
            "Technical evaluations verify that Project Aegis uses Neural Mesh v2 as its primary benchmarking testbed."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_technical_paper"},
    },
    {
        "id": "DOC_006",
        "title": "Biographical Archive: Dr. Alyssa Vance and Contemporary AI",
        "source_type": "synthetic",
        "publication_date": "2023-10-12",
        "source_uri": "synthetic://corpus/doc_006.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "A retrospective on contemporary computing figures highlights the career of Dr. Alyssa Vance. "
            "Historical corporate filings confirm that Dr. Alyssa Vance founded Cognitive Dynamics after departing academia. "
            "The biographical entry corroborates that Dr. Alyssa Vance worked on Project Prometheus between 2021 and 2022. "
            "Her work on distributed representation paved the way for subsequent developments across European research laboratories. "
            "During 2023, Dr. Alyssa Vance collaborated with Dr. Clara Weber to formalize decentralized agent consensus."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_biography", "is_redundant_source": True},
    },
    {
        "id": "DOC_007",
        "title": "Investigative Retraction and Advisory History at Cognitive Dynamics",
        "source_type": "synthetic",
        "publication_date": "2023-11-01",
        "source_uri": "synthetic://corpus/doc_007.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "CONTRADICTION ANALYSIS DISCLOSURE: Disputed founder attribution.\n"
            "An independent retrospective published by technology analysts challenges prevailing corporate narratives. "
            "According to internal governance memorandums, Dr. Alyssa Vance did not found Cognitive Dynamics, "
            "having acted solely as an external scientific consultant during its initial incorporation period. "
            "The memorandum asserts that founding equity was held exclusively by institutional holding entities."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_dispute", "contains_contradiction": True},
    },
    {
        "id": "DOC_008",
        "title": "Global Technology Infrastructure and Site Assessments",
        "source_type": "synthetic",
        "publication_date": "2023-12-04",
        "source_uri": "synthetic://corpus/doc_008.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "SITE DISPUTE DOSSIER:\n"
            "Municipal filings and economic development records indicate conflicting geographical listings. "
            "While European registries list Swiss operations, commercial licensing indicates that "
            "Cognitive Dynamics is located in Bengaluru Tech Corridor under a foreign direct investment initiative. "
            "Additionally, the report notes that Turing Institute of Bengaluru collaborated with Dr. Vikram Patel on local incubation. "
            "Furthermore, Dr. Vikram Patel was employed by Turing Institute of Bengaluru to direct machine intelligence workshops. "
            "Turing Institute of Bengaluru is located in Bengaluru Tech Corridor within the electronic city precinct."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_regional_report", "contains_contradiction": True},
    },
    {
        "id": "DOC_009",
        "title": "Quantum Information Bridges at Qubit Dynamics",
        "source_type": "synthetic",
        "publication_date": "2023-04-22",
        "source_uri": "synthetic://corpus/doc_009.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "The intersection of solid-state qubits and neural decoders represents a burgeoning subfield. "
            "Dr. Tariq Al-Mansoor was employed by Qubit Dynamics Group as principal quantum engineer. "
            "Under his direction, Qubit Dynamics Group developed the QubitSync Protocol to synchronize pulse channels. "
            "Technical memoranda record that Dr. Tariq Al-Mansoor collaborated with Dr. Elena Rostova on quantum error-correcting neural topographies. "
            "Qubit Dynamics Group is located in Zurich Innovation Center near partner physics laboratories. "
            "In high-speed test environments, Qubit Dynamics Group uses QubitSync Protocol for real-time calibration."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_quantum_report"},
    },
    {
        "id": "DOC_010",
        "title": "Project Hyperion and Distributed AI Governance",
        "source_type": "synthetic",
        "publication_date": "2024-01-30",
        "source_uri": "synthetic://corpus/doc_010.txt",
        "raw_text": (
            "SYNTHETIC DOCUMENT: For benchmark purposes only.\n\n"
            "Project Hyperion was established to investigate decentralized governance protocols for autonomous agents. "
            "Dr. Daniel Kim worked on Project Hyperion from its inception in mid-2023. "
            "Later in the year, Dr. Daniel Kim was employed by Apex Robotics Systems to direct autonomous fleet coordination. "
            "Apex Robotics Systems developed the HoloVector Architecture for spatial multi-robot localization. "
            "Apex Robotics Systems is located in Bengaluru Tech Corridor near industrial robotics facilities. "
            "Dr. Daniel Kim collaborated with Dr. Vikram Patel on distributed localization benchmarks. "
            "CRITICAL NEGATIVE TEST CONSTRAINT: Neither Dr. Kim nor Apex Robotics Systems developed any quantum protocols, "
            "leaving quantum-robotic cross-domain queries provably unanswerable under current evidentiary bounds."
        ),
        "metadata": {"benchmark": "KG-RS-01", "classification": "synthetic_governance_report", "unanswerable_boundary": True},
    },
]
