"""Pytest Fixtures and Global Test Configuration for NOESIS."""

import sys
from pathlib import Path

import pytest

# Ensure workspace root is in python path
root_dir = str(Path(__file__).resolve().parent.parent.parent)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from backend.app.graph.in_memory import InMemoryGraphRepository
from backend.app.reasoning.engine import BoundedReasoningEngine
from scripts.seed_graph import seed_database


@pytest.fixture(scope="session")
def seeded_repository():
    """Returns a fresh InMemoryGraphRepository populated with the synthetic benchmark corpus."""
    from backend.app.graph.factory import set_graph_repository
    repo = InMemoryGraphRepository()
    set_graph_repository(repo)
    seed_database(clear_existing=True)
    return repo


@pytest.fixture
def reasoning_engine(seeded_repository):
    """Returns a BoundedReasoningEngine instance backed by the seeded repository."""
    return BoundedReasoningEngine(repository=seeded_repository)
