# Changelog

All notable changes to the NOESIS project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-11-24

### Added
- Evidence-centric ontology with Entity, Claim, Evidence, and Document node specifications.
- Deterministic SHA-256 claim fingerprinting algorithm based on normalized semantic fields.
- Graph repository abstraction supporting both Neo4j persistent storage and in-memory traversal fallback.
- Quotation verification service validating exact source text against character offsets.
- Multi-hop bounded graph reasoning engine supporting 1-hop to 5-hop directional traversal.
- Cycle prevention and multiple reasoning path enumeration.
- Explainable confidence scoring heuristic $C(e) = 0.35Q + 0.30S + 0.20A + 0.15V$.
- Counterfactual evidence ablation engine for evaluating source criticality.
- Contradiction detection engine for opposing polarities and conflicting claims.
- 10 interconnected synthetic documents covering >=25 entities and >=35 claims with ground truth.
- FastAPI REST backend with versioned `/api/v1` routes, dependency injection, CORS, and OpenAPI docs.
- React + TypeScript + Vite investigative workstation with Cytoscape.js canvas and Tailwind styling.
- Comprehensive automated Pytest test suite covering ontology, determinism, reasoning, and schemas.
- Full ISO/IEC/IEEE 29148 requirements traceability matrix and Architecture Decision Records (ADRs).
