"""Shared pytest fixtures for Reasoning graph contracts.

- `neo4j_driver`: one driver per test session; tests are skipped (with the
  reason) when Neo4j is unreachable.
- `cleanup_graph(...)`: removes a contract's own nodes before and after it
  runs, pass or fail, so contract data never accumulates in the shared graph.
- `single(driver, cypher, **params)`: run a read query and return one record.
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


def single(driver, cypher, **params):
    with driver.session(database=NEO4J_DATABASE, default_access_mode="READ") as session:
        return session.run(cypher, **params).single()


def cleanup_graph(driver, *, scenarios=(), assets=(), source_ips=()):
    """Delete this contract's events and test-only nodes. Topology is never touched."""
    with driver.session(database=NEO4J_DATABASE) as session:
        session.run("MATCH (e:Event) WHERE e.scenario_id IN $ids DETACH DELETE e", ids=list(scenarios)).consume()
        session.run("MATCH (a:Asset) WHERE a.asset_id IN $ids DETACH DELETE a", ids=list(assets)).consume()
        # A source IP is removed only when no remaining event refers to it.
        session.run("MATCH (ip:SourceIP) WHERE ip.address IN $ips AND NOT (ip)--() DELETE ip",
                    ips=list(source_ips)).consume()
