"""The single-domain baseline comparison stays consistent with the uncertainty study."""
import random

from presentation.backend.validation import baseline_comparison as bc
from reasoning.uncertainty.bayesian_correlation import load_knowledge_base
from reasoning.uncertainty.evaluate import load_scenarios, operator_view, score_rows


def test_alert_counts_match_the_uncertainty_operator_view():
    scenarios = load_scenarios()
    rows = score_rows(scenarios, load_knowledge_base())
    for split in ("dev", "test"):
        chosen = [s for s in scenarios if s["split"] == split]
        split_rows = [r for r in rows if r["split"] == split]
        result = bc.evaluate_split(chosen, split_rows, random.Random(0), orders=5)
        crisp = operator_view(chosen, split_rows, "crisp")
        abnormal = sum(1 for s in chosen for a in bc.alerts_for(s, split_rows, "isolated"))
        assert result["isolated"]["alerts"] == abnormal
        assert result["dc_guardian"]["alerts"] == crisp["alerts_shown"]
        assert result["dc_guardian"]["incidents_in_one_alert"] == crisp["incidents_fully_linked"]
        # Isolated alerts can show a multi-event incident whole only if it has one event.
        assert result["isolated"]["multi_event_incidents_in_one_alert"] == 0


def test_queue_metrics_on_a_hand_checked_queue():
    truth = {("S", "I1"): {"a", "b"}}
    queue = [{"events": ["n"], "incidents": set()},
             {"events": ["a", "b"], "incidents": {("S", "I1")}}]
    m = bc.queue_metrics(queue, truth)
    assert m["average_precision"] == 0.5
    assert m["alerts_until_every_incident_seen"] == 2
    assert m["alerts_until_every_incident_event_seen"] == 2
