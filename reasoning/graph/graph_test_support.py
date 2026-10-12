"""Helpers shared by the Reasoning graph pytest contracts (imported by name, not via conftest)."""
from ingest_event import NEO4J_DATABASE  # noqa: E402  reasoning/graph is on sys.path (see conftest.py)


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
