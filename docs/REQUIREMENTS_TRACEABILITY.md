# ISO/IEC/IEEE 29148 Requirements Traceability Matrix

This matrix maps functional requirements from the NOESIS PRD to their architectural components, code implementations, and automated test cases.

| Req ID | Requirement Description | Architecture Component | Implementation Module | Automated Test Case | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FR-01** | Document Ingestion & Provenance | Ingestion Service | `backend/app/ingestion/` | `backend/tests/test_ontology.py::test_document_hashing` | **Verified** |
| **FR-02** | Entity Schema & Resolution | Ontology Layer | `backend/app/ontology/models.py` | `backend/tests/test_ontology.py::test_entity_schema` | **Verified** |
| **FR-03** | Relationship & Evidence Grounding | Ontology & Extraction | `backend/app/ontology/models.py` | `backend/tests/test_ontology.py::test_claim_evidence_link` | **Verified** |
| **FR-04** | Deterministic Claim Fingerprinting | Extraction Service | `backend/app/extraction/fingerprint.py` | `backend/tests/test_ontology.py::test_fingerprint_determinism` | **Verified** |
| **FR-05** | Evidence-Native Knowledge Graph | Graph Repository | `backend/app/graph/in_memory.py` & `neo4j.py` | `backend/tests/test_graph_repo.py::test_dual_store_schema` | **Verified** |
| **FR-06** | Structured Query Planning | Reasoning Engine | `backend/app/reasoning/query_plan.py` | `backend/tests/test_reasoning.py::test_query_plan_validation` | **Verified** |
| **FR-07** | Bounded Graph Traversal (1-5 Hops) | Reasoning Engine | `backend/app/reasoning/engine.py` | `backend/tests/test_reasoning.py::test_three_hop_traversal` | **Verified** |
| **FR-08** | Contradiction Detection | Reasoning Engine | `backend/app/reasoning/contradictions.py` | `backend/tests/test_reasoning.py::test_contradiction_detection` | **Verified** |
| **FR-09** | Counterfactual Evidence Ablation | Reasoning Engine | `backend/app/reasoning/ablation.py` | `backend/tests/test_reasoning.py::test_counterfactual_ablation` | **Verified** |
| **FR-10** | Explainable Confidence Heuristic | Reasoning Engine | `backend/app/reasoning/confidence.py` | `backend/tests/test_reasoning.py::test_confidence_heuristic` | **Verified** |
| **FR-11** | Exact Quotation Verification | Extraction Service | `backend/app/extraction/validator.py` | `backend/tests/test_ontology.py::test_quotation_span_validation` | **Verified** |
| **FR-12** | Cycle Prevention in Graph Paths | Reasoning Engine | `backend/app/reasoning/engine.py` | `backend/tests/test_reasoning.py::test_cycle_prevention` | **Verified** |
| **FR-13** | Unanswerable Query Detection | Reasoning Engine | `backend/app/reasoning/engine.py` | `backend/tests/test_reasoning.py::test_unanswerable_query` | **Verified** |
| **FR-14** | REST API & Storage Mode Telemetry | API Layer | `backend/app/api/v1/` | `backend/tests/test_api.py::test_health_and_storage_mode` | **Verified** |
| **FR-15** | Interactive Graph UI & Source Vault | Frontend Application | `frontend/src/` | `npm.cmd run build` | **Verified** |
