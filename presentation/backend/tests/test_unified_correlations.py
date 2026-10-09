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
    assert len(group_edges(edges))==2

def test_zone_isolation_even_with_reused_event_id():
    edges=[
      edge("OP",("maintenance","M1"),("environment","E1"),"OP1","ZONE-A"),
      edge("OP",("maintenance","M1"),("environment","E2"),"OP2","ZONE-B")]
    assert len(group_edges(edges))==2

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
