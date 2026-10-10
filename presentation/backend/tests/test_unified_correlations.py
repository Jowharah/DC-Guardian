from presentation.backend.app.unified_correlations import edge,group_edges

def test_three_domains_merge_only_via_shared_evidence():
    edges=[
      edge("PPE_FACE",("ppe","P1"),("face","F1"),"PF1","ZONE-B"),
      edge("FACE_SSH",("face","F1"),("ssh","S1"),"FS1","ZONE-B")]
    groups=group_edges(edges)
    assert len(groups)==1
    assert len(groups[0]["evidence"])==3
    assert len(groups[0]["edges"])==2
    assert groups[0]["decision_severity"] is None
    assert groups[0]["identity_link_established"] is False

def test_same_zone_unrelated_pairs_remain_separate():
    edges=[
      edge("OP",("maintenance","M1"),("environment","E1"),"OP1","ZONE-B"),
      edge("PPE_FACE",("ppe","P1"),("face","F1"),"PF1","ZONE-B")]
    assert group_edges(edges)==[]
    assert len(group_edges(edges,min_members=2))==2

def test_two_events_are_a_pair_not_a_unified_group():
    pair=[edge("FACE_SSH",("face","F1"),("ssh","S1"),"FS1","ZONE-B")]
    assert group_edges(pair)==[]

def test_unified_group_accepts_any_domains_and_repeated_domains():
    edges=[
      edge("REASONING_CONTEXT",("ssh","S1"),("maintenance","M1"),"X1","ZONE-B"),
      edge("OPERATIONAL",("maintenance","M1"),("environment","E1"),"X2","ZONE-B"),
      edge("REASONING_CONTEXT",("ssh","S2"),("environment","E1"),"X3","ZONE-B")]
    group=group_edges(edges)[0]
    assert [(r["kind"],r["observation_id"]) for r in group["evidence"]]==[
        ("environment","E1"),("maintenance","M1"),("ssh","S1"),("ssh","S2")]
    assert group["domains"]==["CYBERSECURITY","ENVIRONMENTAL","MAINTENANCE"]

def test_zone_isolation_even_with_reused_event_id():
    edges=[
      edge("OP",("maintenance","M1"),("environment","E1"),"OP1","ZONE-A"),
      edge("OP",("maintenance","M1"),("environment","E2"),"OP2","ZONE-B")]
    # Merged across zones, M1 would join a three-event group.
    assert group_edges(edges)==[]
    assert len(group_edges(edges,min_members=2))==2

def test_deterministic_group_id_and_order():
    a=edge("PPE_FACE",("ppe","P1"),("face","F1"),"PF1","ZONE-B")
    b=edge("FACE_SSH",("face","F1"),("ssh","S1"),"FS1","ZONE-B")
    assert group_edges([a,b])==group_edges([b,a])

def test_invalid_domain_and_self_edge_rejected():
    import pytest
    with pytest.raises(ValueError):
        edge("INVALID",("unknown","1"),("ssh","S1"),"X","ZONE-B")
    with pytest.raises(ValueError):
        edge("SELF",("face","F1"),("face","F1"),"X","ZONE-B")

def test_group_does_not_infer_direct_edge():
    edges=[
      edge("PPE_FACE",("ppe","P1"),("face","F1"),"PF1","ZONE-B"),
      edge("FACE_SSH",("face","F1"),("ssh","S1"),"FS1","ZONE-B")]
    group=group_edges(edges)[0]
    assert not any(set([tuple(e["left"]),tuple(e["right"])])==
                   {("ppe","P1"),("ssh","S1")} for e in group["edges"])
