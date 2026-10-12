"""Repository-wide pytest markers turned into skips with a stated reason.

- private_data(*paths): needs local data excluded from Git (face enrollment, datasets,
  the rebuilt RAG knowledge base); skipped when a listed path is missing.
- gpu: needs a CUDA-enabled PyTorch component environment (.venv-ppe, .venv-gru);
  skipped elsewhere. check_all.py runs these with the component interpreter.
- neo4j: needs a running Neo4j; skipped when it cannot be reached.

The same classification drives check_all.py, so local runs, CI and a fresh clone
skip the same tests for the same reasons.
"""
from functools import lru_cache
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def cuda_available():
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001 - no usable torch means no GPU here
        return False


@lru_cache(maxsize=1)
def neo4j_problem():
    try:
        from reasoning.graph.ingest_event import create_driver
        driver = create_driver()
        try:
            driver.verify_connectivity()
        finally:
            driver.close()
        return None
    except Exception as exc:  # noqa: BLE001 - any failure means "not reachable"
        return type(exc).__name__


def pytest_runtest_setup(item):
    private = item.get_closest_marker("private_data")
    if private:
        missing = [p for p in private.args if not (ROOT / p).exists()]
        if missing:
            pytest.skip(f"local data not present (excluded from Git): {', '.join(missing)}")
    if item.get_closest_marker("gpu") and not cuda_available():
        pytest.skip("needs a CUDA-enabled component environment (.venv-ppe or .venv-gru)")
    if item.get_closest_marker("neo4j"):
        problem = neo4j_problem()
        if problem:
            pytest.skip(f"Neo4j not reachable ({problem})")
