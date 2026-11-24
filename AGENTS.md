# AGENTS.md — Multi-Agent Engineering Instructions for NOESIS

## Role and Scope
This document specifies operational guidelines, coding standards, and architectural constraints for AI agents and human developers collaborating on the **NOESIS** code repository.

---

## Architectural Non-Negotiables

1. **Evidence-Native Knowledge Graph**:
   Never create naked direct entity-to-entity edges without an intermediary `Claim` node and at least one linked `Evidence` node. All factual knowledge must be provenance-traceable.

2. **Deterministic Claim Fingerprinting**:
   Every claim identifier must be computed via SHA-256 over normalized fields:
   `sha256(lowercase(subject_id) + "|" + uppercase(predicate) + "|" + lowercase(object_id) + "|" + lowercase(polarity) + "|" + (temporal_scope or ""))`.

3. **Dual-Store Resilience**:
   The backend must support both `Neo4jGraphRepository` (persistent) and `InMemoryGraphRepository` (embedded fallback). When Docker or Neo4j is unavailable, the in-memory engine must execute **actual graph traversal** (DFS/BFS path searching, cycle detection, predicate filtering, evidence aggregation). Mocking or hardcoding demonstration query results is strictly forbidden.

4. **Structured Query Plans**:
   Multi-hop queries must use validated Pydantic query models (`StructuredQueryPlan`). Unrestricted or unvalidated LLM-generated Cypher strings must never be directly executed against the database.

5. **Exact Quotation Verification**:
   Evidence records must contain exact source quotation strings and character offsets (`char_offset_start`, `char_offset_end`). The extraction validator must verify that `document.raw_text[start:end] == quote`. Note that string matching confirms text presence, not semantic correctness.

6. **Explainable Confidence & Ablation**:
   Confidence metrics must strictly adhere to the formula:
   $C(e) = 0.35Q + 0.30S + 0.20A + 0.15V$ and $C(P) = \min_{e \in P} C(e)$.
   Ablation testing must be non-destructive.

---

## Environment & Tooling Rules (Windows PowerShell)

- Always execute Node/NPM via `npm.cmd` and `npx.cmd`.
- Never alter PowerShell execution policies.
- Do not add paid external API dependencies.
- Use explicit type hints on all Python functions and classes.
- Format and lint code with `ruff`.
- Maintain small, focused Git commits using the Conventional Commits specification.
