# NOESIS Scientific Evaluation Protocol
**Project:** NOESIS (Neural-Ontological Evidence Synthesis and Inference System)  
**Conference / Program:** IEEE BMSITM Winter of Projects 2026  
**Document Classification:** Standard Operating Procedure (SOP) & Evaluation Specification  
**Version:** 1.0.0 (Release Baseline)  

---

## 1. Executive Overview and Evaluation Philosophy

The primary objective of NOESIS is to eliminate hallucinations, enforce lexical and semantic evidentiary provenance, and ensure bounded, verifiable multi-hop reasoning over complex multi-document corpora on consumer hardware.

Evaluating neuro-symbolic evidence systems requires a strict methodology that separates:
1. **Oracle-Graph Reasoning:** Evaluating graph traversal, cycle prevention, contradiction isolation, and ablation when graph triples are ground truth.
2. **Natural-Language Query Compilation:** Evaluating translation from natural language questions to symbolic query plans with and without Entity-Anchored Query Compilation (EAQC).
3. **End-to-End Extraction and Reasoning:** Evaluating the full chain from raw unparsed documents (PDF, TXT, Markdown) through chunking, quotation span verification, graph construction, and multi-hop inference.
4. **Contradiction and Evidence Ablation:** Evaluating robustness under conflicting claims and source ablation.
5. **Inference Efficiency and Consumer Hardware Profiling:** Measuring latency decomposition, GPU/CPU memory footprints, and token utilization on constrained hardware (RTX 2050 4 GB VRAM, 16 GB RAM).

> [!IMPORTANT]
> **Scientific Integrity Invariant:** Oracle-graph traversal results MUST NEVER be reported as proof of end-to-end extraction accuracy. Ground truth annotations MUST be specified independently of the system under test; never generate ground-truth labels by running NOESIS or any candidate system.

---

## 2. Research Questions and Formal Hypotheses

### RQ1: Multi-Hop Reasoning Fidelity
*Can bounded symbolic traversal over an evidence-reified graph achieve higher answer exact match and path validity across 1- to 5-hop reasoning chains compared to conventional dense/lexical RAG?*
- **Hypothesis 1 ($H_1$):** As reasoning depth increases from 1 to 5 hops, Conventional RAG recall and exact match degrade exponentially due to passage retrieval fragmentation ($p < 0.01$), whereas NOESIS maintains bounded step-wise path validity.

### RQ2: Evidentiary Traceability and Citation Correctness
*Does reifying claims into explicit evidence nodes with exact character offset verification prevent ungrounded assertions and hallucinated citations?*
- **Hypothesis 2 ($H_2$):** NOESIS achieves 100% lexical quotation validity ($Document.raw\_text[start:end] == quote$) and zero hallucinated source attributions, whereas generative RAG baselines exhibit citation hallucination in $\ge 15\%$ of responses.

### RQ3: Entity-Anchored Query Compilation (EAQC) Effectiveness
*Does deterministic multi-tier mention resolution and anchor locking eliminate entity substitution errors in local LLM query planning?*
- **Hypothesis 3 ($H_3$):** EAQC yields significantly higher query planning accuracy ($\ge 95\%$) compared to unconstrained local LLM generation ($\le 60\%$), completely eliminating distractor corpus entity intrusions.

### RQ4: Contradiction Detection and Counterfactual Ablation
*Can NOESIS accurately isolate polarity and temporal contradictions and identify critical supporting documents without destroying the underlying knowledge graph?*
- **Hypothesis 4 ($H_4$):** NOESIS detects both explicit polarity inversions and temporal scope conflicts with $F_1 \ge 0.90$, and counterfactual ablation correctly identifies single-source dependencies without modifying persistent state.

### RQ5: Repeated Inference and Routing Efficiency
*What is the computational saving of deterministic pattern routing and query plan caching compared to pure generative inference on consumer hardware?*
- **Hypothesis 5 ($H_5$):** Deterministic pattern compilation and warm query plan caching reduce natural language query latency by over two orders of magnitude ($> 100\times$) while eliminating local GPU inference calls entirely.

### RQ6: Consumer Hardware Feasibility
*Can the full NOESIS stack execute reliably within a 4 GB VRAM budget without incurring out-of-memory (OOM) faults or requiring external proprietary APIs?*
- **Hypothesis 6 ($H_6$):** Sequential single-worker GPU locking and 2048-token context window limits permit uninterrupted end-to-end ingestion and inference on an NVIDIA RTX 2050 laptop GPU with zero external cloud dependencies.

---

## 3. Experimental Variables and Controls

| Variable Type | Variable Name | Operationalization / Values |
| :--- | :--- | :--- |
| **Independent** | Architecture Configuration | 1. Conventional RAG (BM25 + qwen3:4b)<br>2. Standard Knowledge Graph (Direct Triples)<br>3. NOESIS w/o EAQC (Unconstrained LLM Planner)<br>4. Full NOESIS (EAQC + Reified Graph + Ablation) |
| **Independent** | Reasoning Depth | 1, 2, 3, 4, 5 hops |
| **Independent** | Evidentiary Condition | Canonical, Contradictory, Ablated, Unanswerable, Adversarial |
| **Independent** | Cache Policy | Cold (uncached), Warm (cached), Disabled |
| **Dependent** | Answer Exact Match (EM) | Binary string equality of normalized entity answer sets |
| **Dependent** | Entity-Set F1 ($F_1$) | Harmonic mean of predicted vs ground-truth entity sets |
| **Dependent** | Path Validity Rate | Binary verification that traversed path exists in graph |
| **Dependent** | Citation Validity | Percentage of citations matching exact document character spans |
| **Dependent** | Contradiction Precision/Recall | Accuracy of flagged contradictory claim pairs |
| **Dependent** | End-to-End Latency | Wall-clock elapsed time (ms) |
| **Dependent** | LLM Invocations | Number of local model forward passes per query |
| **Controlled** | Model Backbone | Ollama `qwen3:4b` (`qwen3:4b-instruct`) |
| **Controlled** | Sampling Temperature | `temperature = 0.0` (greedy deterministic decoding) |
| **Controlled** | Context Length | `num_ctx = 2048` |
| **Controlled** | Hardware Environment | Intel i5-13420H, 16 GB RAM, NVIDIA RTX 2050 (4 GB VRAM) |
| **Controlled** | Storage Mode | `InMemoryGraphRepository` & `Neo4j Community Edition` |

---

## 4. Benchmark Partitioning and Leakage Prevention

### 4.1 Split Distribution
The benchmark suite (**NVS-100**) consists of exactly 100 manually annotated cases divided into:
- **Development Split (60%):** 60 cases used for tuning prompt templates, regex boundary heuristics, and ablation thresholds.
- **Held-Out Test Split (40%):** 40 cases reserved exclusively for final evaluation.

### 4.2 Split Leakage Prevention Rule
To prevent data leakage:
1. Every paraphrased query case MUST reside in the **same split** (Dev or Test) as its underlying canonical question.
2. Canonical entities introduced only in test cases must never be hardcoded into prompt few-shot examples or regex pattern matchers.

---

## 5. Evaluation Phases

```
+--------------------------------------------------------------------------+
|                       Evaluation Protocol Phases                         |
+--------------------------------------------------------------------------+
|  Phase A: Oracle-Graph Reasoning                                         |
|  - Symbolic query execution over pre-seeded ground truth graph           |
|  - Tests: Multi-hop DFS/BFS, cycle avoidance, directional traversal     |
+--------------------------------------------------------------------------+
|  Phase B: Natural-Language Query Compilation                             |
|  - Natural language question -> StructuredQueryPlan                     |
|  - Tests: Entity anchoring, start entity accuracy, predicate accuracy    |
+--------------------------------------------------------------------------+
|  Phase C: End-to-End Extraction & Reasoning                              |
|  - Raw documents -> Ingestion -> Extraction -> Graph -> Traversal -> Ans|
|  - Tests: Entity extraction F1, claim quotation validation, final answer |
+--------------------------------------------------------------------------+
|  Phase D: Contradiction & Evidence Ablation                              |
|  - Conflicting document ingestion & counterfactual source removal       |
|  - Tests: Contradiction F1, single-source dependency identification      |
+--------------------------------------------------------------------------+
|  Phase E: Performance & Latency Decomposition                            |
|  - Profiling on RTX 2050: Cold load, warm inference, traversal latency  |
|  - Tests: Routing telemetry, tokens/sec, GPU VRAM peak                   |
+--------------------------------------------------------------------------+
```

---

## 6. Threats to Validity

1. **Internal Validity:**
   - *Threat:* Generative LLM responses may vary across runs.
   - *Mitigation:* `temperature=0` is enforced globally; seed is fixed; greedy decoding is validated.
2. **Construct Validity:**
   - *Threat:* Lexical string matching might reward surface token overlap rather than genuine factual understanding.
   - *Mitigation:* Entity matching requires canonical identifier resolution; citations require exact character offset containment.
3. **External Validity:**
   - *Threat:* Synthetic research corpora may not reflect all nuances of messy natural prose.
   - *Mitigation:* Section 9 pilot introduces real peer-reviewed scientific literature (Transformer and RAG papers) alongside the synthetic suite.
4. **Conclusion Validity:**
   - *Threat:* Small sample sizes in natural language pilot runs.
   - *Mitigation:* Full 100-case structured benchmark is run; sample size denominators ($N$) and confidence bounds are explicitly reported.

---

## 7. Reproducibility Checklist
To reproduce all reported metrics:
1. Ensure Ollama is running locally with `qwen3:4b`:
   `ollama list` -> confirm `qwen3:4b:latest`
2. Run automated test suite:
   `python -m pytest backend/tests -v`
3. Execute benchmark runner:
   `python evaluation/run_benchmark.py --system noesis --mode structured --split all`
4. Inspect persisted outputs in `evaluation/results/<experiment_id>/`.
