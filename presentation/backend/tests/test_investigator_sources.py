from presentation.backend.app.investigator_sources import unified_sources,operational_sources,single_sources

def test_unified_sources_are_only_supplied_references():
    result=unified_sources({"evidence_refs":[{"kind":"ssh","observation_id":"S1"},{"kind":"ppe","observation_id":"P1"}]})
    assert [(r["kind"],r["id"]) for r in result]==[("ssh","S1"),("ppe","P1")]

def test_operational_sources_deduplicate_graph_ids():
    result=operational_sources({"maintenance":{"event_id":"M1"},"environment":{"event_id":"E1"},
                                "evidence_event_ids":["M1","GRAPH1"]})
    assert [r["id"] for r in result]==["M1","E1","GRAPH1"]

def test_single_source_has_no_inferred_correlation():
    result=single_sources({"kind":"face","evidence_id":"F1"})
    assert result==[{"kind":"face","id":"F1","role":"saved_source_evidence"}]
