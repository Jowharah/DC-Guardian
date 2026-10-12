"""Shared pytest fixtures for Reasoning graph contracts.

- `neo4j_driver`: one driver per test session; tests are skipped (with the
  reason) when Neo4j is unreachable.
- `cleanup_graph(...)` (graph_test_support.py): removes a contract's own nodes before and after it
  runs, pass or fail, so contract data never accumulates in the shared graph.
- `single(driver, cypher, **params)` (graph_test_support.py): run a read query and return one record.
"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# The contracts import Reasoning modules by bare name, as the script-style
# contracts always have.
for directory in (PROJECT_ROOT, PROJECT_ROOT / "reasoning" / "adapters",
                  PROJECT_ROOT / "reasoning" / "topology", PROJECT_ROOT / "reasoning" / "graph"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))

from ingest_event import NEO4J_DATABASE, create_driver  # noqa: E402


@pytest.fixture(scope="session")
def neo4j_driver():
    try:
        driver = create_driver()
    except Exception as exc:
        pytest.skip(f"Neo4j not reachable ({type(exc).__name__}); graph contracts need a running database")
    yield driver
    driver.close()


# Helpers live in graph_test_support.py: a module named conftest would clash with
# the repository-root conftest.py when imported by name.
from graph_test_support import cleanup_graph, single  # noqa: E402,F401
