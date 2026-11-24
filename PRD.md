# Product Requirements Document (PRD)
## NOESIS — Neural-Ontological Evidence Synthesis and Inference System

**Project:** IEEE BMSITM – Winter of Projects 2026  
**Problem Statement:** KG-RS-01 | Knowledge Graph Reasoning  
**Team:** Navya Nawal, Gaurav S, KK Praveen  
**Development Window:** 48 Hours  
**Version:** 1.0  
**Environment:** Google Antigravity + Gemini Pro  

---

## 1. Project Strategy
The strongest differentiator of NOESIS is not document processing or an AI chatbot. It is the combination of four core capabilities:
1. **Evidence-native knowledge graph construction**: Reifying claims into dedicated nodes linked to source evidence.
2. **Explainable multi-hop reasoning**: Bounded graph traversal returning complete, verifiable paths.
3. **Contradiction-aware inference**: Detecting opposing claims without majority-vote bias.
4. **Counterfactual evidence testing**: Non-destructive evidence ablation to identify critical vs redundant sources.

The target is a research-grade, demonstrable MVP with a defensible methodology, reproducible experiments, measurable results, and a clear technical contribution.

---

## 2. Product Definition
- **Product Name:** NOESIS
- **Product Category:** Knowledge graph reasoning engine
- **Primary Domain:** Research, technology, and innovation intelligence
- **Primary User:** Researchers and investigative analysts
- **Secondary Users:** Enterprises, policy analysts, legal researchers
- **Input:** Plain text and PDF documents
- **Processing:** Entity extraction, relationship extraction, graph construction, and bounded inference
- **Output:** Evidence-backed answers with explicit graph paths, confidence heuristics, and conflict warnings
- **Differentiators:** Contradiction detection and counterfactual evidence ablation

### Research Question
> *Can evidence-grounded knowledge graph reasoning improve the accuracy, explainability and robustness of multi-document question answering compared with conventional retrieval-augmented generation (RAG)?*

---

## 3. Scope and Priority
| Feature | Priority | Target |
| :--- | :--- | :--- |
| TXT and PDF Ingestion | P0 | Fully functional |
| Entity Extraction & Schemas | P0 | Fully functional |
| Relationship Extraction | P0 | Fully functional |
| Neo4j Integration + In-Memory Fallback | P0 | Fully functional |
| Evidence Provenance Tracking | P0 | Fully functional |
| Multi-hop Reasoning (1-5 hops) | P0 | Fully functional |
| Interactive Cytoscape.js Visualization | P0 | Fully functional |
| Source Evidence Inspection & Offset Check | P0 | Fully functional |
| Contradiction Detection | P0 | Controlled supported cases |
| Counterfactual Testing (Ablation) | P0 | Source-removal simulation |
| Confidence & Robustness Scoring | P0 | Transparent heuristic |
| Conventional RAG Baseline | P1 | Experimental comparison |
| Semantic Search (FAISS) | P1 | Secondary retrieval index |

---

## 4. Evidence-Centric Graph Schema

### Node Labels
- **`Entity`**: `id`, `canonical_name`, `type`, `aliases`, `metadata`
- **`Claim`**: `id` (deterministic SHA-256 fingerprint), `subject_id`, `predicate`, `object_id`, `polarity`, `confidence`, `temporal_scope`
- **`Evidence`**: `id`, `claim_id`, `document_id`, `quote`, `page`, `chunk_id`, `char_offset_start`, `char_offset_end`
- **`Document`**: `id`, `title`, `source_type`, `publication_date`, `source_uri`, `content_hash`, `ingestion_timestamp`, `raw_text`

### Relationships
- `(Entity)-[:SUBJECT_OF]->(Claim)`
- `(Claim)-[:OBJECT]->(Entity)`
- `(Claim)-[:SUPPORTED_BY]->(Evidence)`
- `(Evidence)-[:FROM_DOCUMENT]->(Document)`
- `(Claim)-[:CONTRADICTS]->(Claim)`

---

## 5. Confidence and Robustness Model

### Claim Confidence Heuristic
$$C(e) = 0.35Q + 0.30S + 0.20A + 0.15V$$
Where:
- $Q \in [0, 1]$: Evidence quality indicator
- $S \in [0, 1]$: Independent-source support count (normalized)
- $A \in [0, 1]$: Agreement among eligible sources (penalized by contradictions)
- $V \in [0, 1]$: Evidence validation indicator (exact quotation string match in document)

### Multi-Hop Path Score
$$C(P) = \min_{e \in P} C(e)$$
The path score is strictly limited by its weakest claim.

### Evidence Robustness Score
$$R(a) = \frac{1}{N} \sum_{i=1}^N \mathbf{1}[\text{claim remains supported without } d_i]$$
Identifies whether conclusions survive source-removal tests.
