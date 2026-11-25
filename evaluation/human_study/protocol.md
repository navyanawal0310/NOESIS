# NOESIS Investigative Challenge 50 (NIC-50) Human Validation Protocol

## 1. Study Overview & Purpose

The **NOESIS Investigative Challenge (NIC-50)** is a controlled user study protocol designed to evaluate human research productivity, fact-finding speed, evidence verification accuracy, and user cognitive load when conducting scientific intelligence synthesis.

The study compares two experimental conditions:
1. **Condition A (NOESIS-Assisted)**: Participants investigate research questions using the NOESIS Evidence Graph interface (natural language query compilation, graph visualizer, quotation inspector, and dialectical contradiction / ablation tools).
2. **Condition B (Manual / Conventional Document Search)**: Participants investigate the identical research questions using standard keyword search (Ctrl+F) over raw synthetic corpus text documents without graph acceleration.

---

## 2. Participant Cohort & Sampling

- **Cohort Size**: 5 domain evaluators / researchers ($N = 5$).
- **Task Count**: 10 distinct investigative tasks per participant ($K = 10$).
- **Total Task Runs**: $5 \times 10 = 50$ evaluation sessions.
- **Assignment**: Within-subjects randomized crossover design (5 tasks in Condition A, 5 tasks in Condition B per participant, counterbalanced).
- **Prerequisites**: Basic familiarity with scientific literature investigation and academic knowledge retrieval.

---

## 3. Investigative Tasks (10 Tasks)

| Task ID | Category | Objective | Time Ceiling |
| :--- | :--- | :--- | :---: |
| **`NIC-01`** | Entity Discovery | Identify primary founder and initial project involvement | 5 min |
| **`NIC-02`** | Single-Hop Fact Retrieval | Verify technology development and exact citation offset | 5 min |
| **`NIC-03`** | Two-Hop Transitive Transit | Trace institutional partner collaborations | 5 min |
| **`NIC-04`** | Three-Hop Inference | Discover technology developed by spinout from umbrella lab | 5 min |
| **`NIC-05`** | Four-Hop Deep Lineage | Trace cross-institutional personnel and hardware usage | 5 min |
| **`NIC-06`** | Dialectical Contradiction | Detect contradictory headquarters locations and conflicting docs | 5 min |
| **`NIC-07`** | Evidence Ablation | Identify critical document whose removal collapses reasoning | 5 min |
| **`NIC-08`** | Knowledge Gap Abstention | Correctly identify ungrounded query and abstain from answering | 5 min |
| **`NIC-09`** | Adversarial Resistance | Reject misleading prompt injection and maintain grounded truth | 5 min |
| **`NIC-10`** | Paraphrased Invariance | Resolve complex syntactically altered natural language inquiry | 5 min |

---

## 4. Quantitative & Qualitative Metrics

1. **Task Completion Rate ($TCR$)**: Percentage of tasks solved within the 5-minute time ceiling.
2. **Time to Discovery ($TTD$)**: Wall-clock seconds from task assignment to candidate answer submission.
3. **Citation Precision ($CP$)**: Fraction of cited supporting documents that genuinely prove the claim.
4. **Answer Accuracy ($ACC$)**: Binary score (1 if correct terminal entity identified, 0 otherwise).
5. **System Usability Scale ($SUS$)**: Standardized 10-item Likert survey scored 0–100.
6. **Cognitive Workload (NASA-TLX Short)**: 5-point subjective mental demand rating.

---

## 5. Experimental Ethics & Pending Authorization

> [!IMPORTANT]
> **Study Status: PENDING / PROPOSAL STAGE**
> Human subject evaluation has not yet been conducted. No formal Institutional Review Board (IRB) approval, ethical clearance, or official IEEE compliance certification has been requested, granted, or claimed. The protocol below constitutes a proposed experimental methodology awaiting formal authorization and participant onboarding.

- **Participation**: Entirely voluntary with informed consent prior to session commencement.
- **Privacy & Anonymity**: No personally identifiable information (PII) is recorded or retained; participants are designated exclusively by pseudo-anonymous identifiers (`P01`–`P05`).
- **Data Governance**: Collected task timings, accuracy ratings, and Likert survey responses will be stored in anonymized CSV/JSON format for peer-review audit.
- **Ethical Alignment**: The proposed protocol is designed in accordance with standard non-invasive software usability evaluation guidelines, subject to institutional clearance before data acquisition.
