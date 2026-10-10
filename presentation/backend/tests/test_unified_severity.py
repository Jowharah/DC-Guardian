"""Provisional group severity and verdict-aware unified groups."""
from presentation.backend.app.unified_severity import members_with_review,group_severity,POLICY
from presentation.backend.app.unified_decision import evaluate

GROUP={"id":"G1","zone_id":"ZONE-A","edges":[{"type":"PHYSICAL_IMAGE"},{"type":"FACE_SSH_CONTEXT"}],
       "evidence":[{"kind":"face","observation_id":"F1"},{"kind":"ppe","observation_id":"P1"},
                   {"kind":"ssh","observation_id":"S1"}]}
STATES={("face","F1"):{"state":"UNAUTHORIZED","detector_abnormal":True},
        ("ppe","P1"):{"state":"PPE_NON_COMPLIANT","detector_abnormal":True},
        ("ssh","S1"):{"state":"HIGH_CONFIDENCE_ANOMALY","detector_abnormal":True}}
CLEARED_PPE={"verdict":"OVERRIDDEN","model_status":"NON_COMPLIANT","effective_status":"COMPLIANT",
             "recorded_at":"2026-10-10T17:34:35+00:00","source":"HUMAN_OVERRIDE"}

def members(human=None,summaries=None):
    return members_with_review(GROUP,STATES,human or {},summaries or {})

def test_three_active_concern_domains_are_high():
    result=group_severity(members())
    assert result["severity"]=="HIGH"
    assert "MULTI_DOMAIN_CORRELATED_RISK" in result["rules_triggered"]
    assert "UNAUTHORIZED_PHYSICAL_ACCESS_EVIDENCE" in result["rules_triggered"]
    assert result["policy"]==POLICY and result["provisional"] is True

def test_cleared_member_stays_marked_and_lowers_severity():
    m=members({("ppe","P1"):False},{("ppe","P1"):CLEARED_PPE})
    ppe=next(x for x in m if x["kind"]=="ppe")
    assert ppe["cleared_by_human"] is True and ppe["active_concern"] is False
    assert ppe["effective_state"]=="COMPLIANT" and ppe["detector_state"]=="PPE_NON_COMPLIANT"
    result=group_severity(m)
    assert result["severity"]=="MEDIUM"
    assert result["active_concern_domains"]==["CYBERSECURITY","PHYSICAL_SECURITY"]

def test_human_escalation_counts_as_concern():
    states={**STATES,("ppe","P1"):{"state":"COMPLIANT","detector_abnormal":False}}
    plain=members_with_review(GROUP,states,{},{})
    assert next(x for x in plain if x["kind"]=="ppe")["active_concern"] is False
    escalated=members_with_review(GROUP,states,{("ppe","P1"):True},{})
    assert next(x for x in escalated if x["kind"]=="ppe")["active_concern"] is True

def test_no_active_concerns_means_no_severity():
    m=members({k:False for k in STATES},{})
    assert group_severity(m)["severity"] is None

def test_disposition_carries_group_severity_not_specialist_severity():
    m=members()
    group={**GROUP,"members":m,"decision_severity":"HIGH","severity_policy":POLICY,
           "severity_rules_triggered":["MULTI_DOMAIN_CORRELATED_RISK"]}
    result=evaluate(group,{"cybersecurity":{"grounding_status":"SUPPORTED","severity":"LOW"}})
    assert result["severity"]=="HIGH"
    assert result["severity_policy"]==POLICY
    assert result["standalone_severity_inherited"] is False

def test_disposition_drops_review_reason_for_human_verified_members():
    unreviewed=evaluate({**GROUP,"members":members()},{"cybersecurity":{"grounding_status":"SUPPORTED"}})
    assert "PPE_EVIDENCE_REQUIRES_SOURCE_REVIEW" in unreviewed["review_reasons"]
    cleared=evaluate({**GROUP,"members":members({("ppe","P1"):False},{("ppe","P1"):CLEARED_PPE})},
                     {"cybersecurity":{"grounding_status":"SUPPORTED"}})
    assert "PPE_EVIDENCE_REQUIRES_SOURCE_REVIEW" not in cleared["review_reasons"]
    assert "HUMAN_CLEARED_MEMBERS_PRESENT" in cleared["review_reasons"]

def test_human_authorized_face_suppresses_graph_unauthorized_reason():
    graph={"recognition_status":"RECOGNIZED","zone_authorization":{"status":"UNAUTHORIZED",
           "source":"NEO4J_READ_ONLY","reason":"GRAPH_RELATIONSHIP_CHECK"}}
    flagged=evaluate({**GROUP,"members":members()},{"physical_security":{"grounding_status":"SUPPORTED"}},[graph])
    assert "RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE" in flagged["review_reasons"]
    authorized={**graph,"human_review":{"source":"HUMAN_OVERRIDE","effective_status":"AUTHORIZED"}}
    cleared=evaluate({**GROUP,"members":members()},{"physical_security":{"grounding_status":"SUPPORTED"}},[authorized])
    assert "RECOGNIZED_IDENTITY_NOT_AUTHORIZED_FOR_DECLARED_ZONE" not in cleared["review_reasons"]

def test_severity_without_reasons_still_requires_review():
    group={"id":"G2","zone_id":"ZONE-A","edges":[],"evidence":[],"members":[],
           "decision_severity":"MEDIUM","severity_rules_triggered":["X"]}
    result=evaluate(group,{"operations":{"grounding_status":"SUPPORTED"}})
    assert result["status"]=="REVIEW_REQUIRED" and result["response_mode"]=="HUMAN_REVIEW"

def test_member_verdict_after_group_review_flags_re_review():
    from presentation.backend.app.human_review_audit import connect
    from presentation.backend.app.unified_decision import member_verdicts_changed
    group={**GROUP,"members":members({("ppe","P1"):False},{("ppe","P1"):CLEARED_PPE})}
    assert member_verdicts_changed(group,None) is False
    def review_at(stamp):
        with connect() as db:
            db.execute("INSERT INTO human_review_audit VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                       ("DCG-HR-"+stamp,"G1","ZONE-A","r",stamp,"NEEDS_FOLLOW_UP","x"*15,"s","p","EVIDENCE_REVIEW_REQUIRED","GENESIS","h"))
    review_at("2026-10-10T17:00:00+00:00")
    assert member_verdicts_changed(group,None) is True
    review_at("2026-10-10T18:00:00+00:00")
    assert member_verdicts_changed(group,None) is False
