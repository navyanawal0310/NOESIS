# ADR-0001: Evidence-Centric Claim Reification

## Status
Accepted

## Context
Standard knowledge graph representations model relationships as direct directed edges: `(Subject)-[:PREDICATE]->(Object)`. 
While efficient for simple querying, this design severely limits research and investigative intelligence:
1. Relationships cannot easily link to multiple independent sources with verbatim text quotations and character offsets.
2. Contradictory statements (e.g. Document A claims Dr. X founded Lab Y, while Document B claims Dr. X was an employee, not a founder) require modifying the edge or asserting conflicting edges without provenance.
3. Simulating counterfactual evidence ablation (evaluating whether a multi-hop conclusion survives the removal of a specific document) becomes computationally messy.

## Decision
We reify every relationship into a dedicated `Claim` node:
- `(Entity)-[:SUBJECT_OF]->(Claim)`
- `(Claim)-[:OBJECT]->(Entity)`
- `(Claim)-[:SUPPORTED_BY]->(Evidence)`
- `(Evidence)-[:FROM_DOCUMENT]->(Document)`
- `(Claim)-[:CONTRADICTS]->(Claim)`

Claims receive deterministic identifiers via SHA-256 fingerprinting of their normalized fields. Multiple documents asserting the same fact attach their `Evidence` nodes to the same `Claim` node.

## Consequences
- **Positive**: Enables granular citation tracking, explicit contradiction detection, and non-destructive counterfactual ablation.
- **Trade-off**: Increases path length by a factor of 2 in raw graph edges (Entity -> Claim -> Entity = 1 semantic hop). The query traversal engine accounts for this seamlessly.
