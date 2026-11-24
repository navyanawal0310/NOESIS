# ADR-0002: Dual Persistent and In-Memory Graph Storage Strategy

## Status
Accepted

## Context
NOESIS targets enterprise and research environments where Neo4j Community Edition is the preferred persistent graph database. However, in restricted sandboxes, air-gapped workstations, CI pipelines, or developer environments without active Docker daemons, strict reliance on Neo4j would prevent execution.

## Decision
We introduce an explicit repository interface: `BaseGraphRepository`.
Two implementations are provided:
1. `Neo4jGraphRepository`: Connects to Neo4j via official Bolt driver using parameterized Cypher and managed transactions.
2. `InMemoryGraphRepository`: A high-performance Python-native graph store maintaining node indexes and adjacency structures. It implements full bounded graph search (DFS/BFS), cycle detection, directional filtering, and evidence joins.

The application automatically tests Neo4j availability on boot; if unreachable, it gracefully falls back to `InMemoryGraphRepository` and exposes the active mode in `GET /api/v1/health`.

## Consequences
- **Positive**: Guaranteed zero-dependency runnability anywhere Python runs, without sacrificing actual graph traversal capabilities.
- **Trade-off**: Requires maintaining parity between Cypher queries and Python adjacency traversal logic.
