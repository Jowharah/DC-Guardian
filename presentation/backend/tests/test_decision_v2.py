"""DCG-DECISION-v2: single-event policy, linkage escalation, live wiring."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from decision import rules_v2
from presentation.backend.app.unified_severity import members_with_review, group_severity
from presentation.backend.app.standalone_decision import node_decision

T0 = datetime(2026, 10, 11, 12, 0, tzinfo=timezone.utc)


def ev(domain, state, minute, **extra):
    return {"domain": domain, "state": state, "timestamp": (T0 + timedelta(minutes=minute)).isoformat(), **extra}


def test_single_event_policy_is_conservative():
    cases = {("SAFETY", "PPE_NON_COMPLIANT"): "LOW", ("MAINTENANCE", "AT_RISK"): "LOW",
             ("ENVIRONMENTAL", "HIGH_TEMPERATURE"): "LOW", ("ENVIRONMENTAL", "SMOKE_DETECTED"): "LOW",
             ("PHYSICAL_SECURITY", "UNKNOWN_PERSON"): "MEDIUM", ("PHYSICAL_SECURITY", "UNAUTHORIZED"): "MEDIUM",
             ("CYBERSECURITY", "ANOMALY_CANDIDATE"): "MEDIUM", ("CYBERSECURITY", "ANOMALOUS"): "MEDIUM"}
    for (domain, state), level in cases.items():
        assert rules_v2.event_severity({"domain": domain, "state": state})[0] == level, (domain, state)
    for domain, state in (("SAFETY", "COMPLIANT"), ("MAINTENANCE", "HEALTHY"), ("ENVIRONMENTAL", "NORMAL"),
                          ("PHYSICAL_SECURITY", "RECOGNIZED")):
        assert rules_v2.event_severity({"domain": domain, "state": state})[0] is None
    assert rules_v2.event_severity({"domain": "PHYSICAL_SECURITY", "state": "RECOGNIZED",
                                    "authorization": "UNAUTHORIZED"})[0] == "MEDIUM"


def test_known_mechanism_within_ten_minutes_escalates_one_level():
    linked = rules_v2.decide_group([ev("ENVIRONMENTAL", "HIGH_TEMPERATURE", 0), ev("MAINTENANCE", "AT_RISK", 9)])
    assert linked["base_severity"] == "LOW" and linked["severity"] == "MEDIUM" and linked["escalated"]
    assert "LINKED_GROUP_ESCALATION" in linked["rules_triggered"]
    slow = rules_v2.decide_group([ev("ENVIRONMENTAL", "HIGH_TEMPERATURE", 0), ev("MAINTENANCE", "AT_RISK", 14)])
    assert slow["severity"] == "LOW" and not slow["escalated"]


def test_many_domains_without_a_mechanism_do_not_escalate():
    group = [ev("CYBERSECURITY", "ANOMALY_CANDIDATE", 0), ev("ENVIRONMENTAL", "HIGH_TEMPERATURE", 1),
             ev("SAFETY", "PPE_NON_COMPLIANT", 2), ev("MAINTENANCE", "AT_RISK", 20)]
    # Maintenance is 20 min out; cyber/environment/safety have no known mechanism among them.
    result = rules_v2.decide_group(group)
    assert result["severity"] == "MEDIUM" and not result["escalated"]


def test_unauthorized_person_with_cyber_reaches_high():
    result = rules_v2.decide_group([ev("PHYSICAL_SECURITY", "RECOGNIZED", 0, authorization="UNAUTHORIZED"),
                                    ev("CYBERSECURITY", "HIGH_CONFIDENCE_ANOMALY", 6)])
    assert result["severity"] == "HIGH" and result["base_severity"] == "MEDIUM"
    record = rules_v2.decision_record(result["severity"], result["rules_triggered"], group=True)
    assert record["escalation_required"] and record["autonomous_action_allowed"] is False
    assert record["validation_status"] == rules_v2.VALIDATION_STATUS


def test_known_mechanisms_match_the_frozen_knowledge_base():
    kb = json.loads(Path("reasoning/uncertainty/knowledge_base.json").read_text(encoding="utf-8"))
    assert {frozenset(x["pair"]) for x in kb["domain_mechanisms"]["KNOWN"]} == set(rules_v2.KNOWN_MECHANISMS)


def test_fixed_rule_is_the_dev_split_selection():
    from presentation.backend.validation.decision_v2_validation import groups, select
    from reasoning.uncertainty.bayesian_correlation import load_knowledge_base
    from reasoning.uncertainty.evaluate import load_scenarios, score_rows
    scenarios = [s for s in load_scenarios() if s["split"] == "dev"]
    chosen, _ = select(groups(scenarios, score_rows(scenarios, load_knowledge_base())))
    assert chosen == rules_v2.SELECTED_LINKAGE_RULE


GROUP = {"id": "G1", "zone_id": "ZONE-A", "evidence": [
    {"kind": "face", "observation_id": "F1"}, {"kind": "ppe", "observation_id": "P1"}, {"kind": "ssh", "observation_id": "S1"}]}
STATES = {("face", "F1"): {"state": "UNAUTHORIZED", "detector_abnormal": True},
          ("ppe", "P1"): {"state": "PPE_NON_COMPLIANT", "detector_abnormal": True},
          ("ssh", "S1"): {"state": "HIGH_CONFIDENCE_ANOMALY", "detector_abnormal": True}}


def node(kind, oid, state, minute, server=None):
    return {"kind": kind, "id": oid, "zone_id": "ZONE-A", "server_id": server, "state": state,
            "times": [T0 + timedelta(minutes=minute)], "attributes": {}}


NODES = {("face", "F1"): node("face", "F1", "UNAUTHORIZED", 0), ("ppe", "P1"): node("ppe", "P1", "PPE_NON_COMPLIANT", 1),
         ("ssh", "S1"): node("ssh", "S1", "HIGH_CONFIDENCE_ANOMALY", 7, "SRV-A1-01")}


def test_live_group_uses_v2_and_keeps_cleared_members_out():
    result = group_severity(members_with_review(GROUP, STATES, {}, {}), NODES)
    assert result["policy"] == "DCG-DECISION-v2" and result["provisional"] is False
    assert result["severity"] == "HIGH" and result["escalated"]
    assert result["linkage"]["unauthorized_with_cyber"] and result["linkage"]["time_spread_minutes"] == 7
    cleared = {"verdict": "OVERRIDDEN", "model_status": "NON_COMPLIANT", "effective_status": "COMPLIANT",
               "recorded_at": "x", "source": "HUMAN_OVERRIDE"}
    without_ppe = group_severity(members_with_review(GROUP, STATES, {("ppe", "P1"): False}, {("ppe", "P1"): cleared}), NODES)
    assert without_ppe["active_concern_domains"] == ["CYBERSECURITY", "PHYSICAL_SECURITY"]
    assert without_ppe["severity"] == "HIGH"


def test_standalone_decision_follows_human_verdicts():
    face = node("face", "F2", "RECOGNIZED", 0)
    assert node_decision(face)["severity"] is None
    unknown = {"verdict": "OVERRIDDEN", "effective_status": "UNKNOWN_PERSON", "abnormal": True}
    assert node_decision(face, unknown)["severity"] == "MEDIUM"
    ppe = node("ppe", "P2", "PPE_NON_COMPLIANT", 0)
    assert node_decision(ppe)["severity"] == "LOW"
    cleared = node_decision(ppe, {"verdict": "OVERRIDDEN", "effective_status": "COMPLIANT", "abnormal": False})
    assert cleared["severity"] is None and cleared["decision_rules_triggered"] == ["INPUT_CLEARED_BY_HUMAN_VERDICT"]
    confirmed = node_decision(ppe, {"verdict": "CONFIRMED", "effective_status": "NON_COMPLIANT", "abnormal": None})
    assert confirmed["severity"] == "LOW" and confirmed["input_source"] == "DETECTOR"
