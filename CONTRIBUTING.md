# Contributing to NOESIS

Thank you for contributing to the NOESIS research prototype.

## Standards and Guidelines

### 1. Requirements Traceability
All functional additions must reference a requirement ID from [docs/REQUIREMENTS_TRACEABILITY.md](docs/REQUIREMENTS_TRACEABILITY.md) adhering to ISO/IEC/IEEE 29148 principles.

### 2. Python Code Quality
- All backend code must pass `ruff check backend` and `pytest backend/tests`.
- Strict type hinting is enforced across all modules (`mypy` / Python 3.11 type hints).
- Pydantic models must be used for data validation at API and repository boundaries.

### 3. Frontend Code Quality
- TypeScript with strict null checks.
- Tailwind CSS utility classes adhering to the dark graphite + amber palette.
- Cytoscape.js components must remain decoupled from business logic.

### 4. Commit Conventions
Use Conventional Commits:
- `feat(...)`: New capability or endpoint
- `fix(...)`: Bug fix
- `docs(...)`: Documentation updates
- `test(...)`: Unit or integration test suites
- `refactor(...)`: Non-functional code cleanup
- `chore(...)`: Configuration or dependency adjustments
