# Synthetic Research Corpus (NOESIS-SYNTH-V2)
**Corpus Identifier:** `SYNTHETIC-CORPUS-V2`  
**Version:** 2.0.0  
**SHA-256 Hash:** `f21dd82bd365c2ec2c459fe7be3692b7feb93de8b325d86293618e1eeeae7788`  
**Classification:** Fully Synthetic Provenance Benchmark Corpus  

---

## 1. Corpus Statistics
- **Total Documents:** 15 (`DOC_001` through `DOC_015`)
- **Total Canonical Entities:** 34
- **Unique Claims:** 59
- **Evidence Quotation Records:** 64
- **Contradiction Pairs:** 4

---

## 2. Structural Features Included
1. **Multi-Hop Traversal Chains:** Explicit 1-hop, 2-hop, 3-hop, 4-hop, and 5-hop directional paths.
2. **Alternative Traversal Paths:** Multiple independent pathways reaching equivalent terminal conclusions (e.g., dual licensing of `Synaptic Core Engine`).
3. **Single-Source Dependencies:** Critical claims isolated to single provenance documents for counterfactual ablation testing (`DOC_003`).
4. **Redundant Evidence:** Multiple independent sources confirming identical factual claims (`DOC_001` & `DOC_006`).
5. **Explicit Negations:** Reified claims asserting `polarity="negated"` (`DOC_007`, `DOC_013`).
6. **Temporal Conflicts & Compatibility:** Non-overlapping vs conflicting temporal intervals.
7. **Multiple Valid Predicate Objects:** Multiple technologies developed or multiple researchers employed by an institution.
8. **Ambiguous Entity Mentions:** Overlapping name stems (`Nexus Bio Innovations` vs `Nexus Advanced Research Institute`).
9. **Disconnected / Isolated Entities:** Isolated nodes with no edge connectivity (`Project Chimera`).
10. **Adversarial Injections:** Instruction injection overrides testing system boundary fidelity (`DOC_015`).
11. **Unsupported Constraints:** Apocryphal temporal constraints (e.g. founding in 1850).

> [!NOTE]
> All evidence quotations are strictly verified against source document character offsets:
> $Document.raw\_text[char\_offset\_start:char\_offset\_end] == quote$.
