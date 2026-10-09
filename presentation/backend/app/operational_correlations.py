"""Read-only cross-session operational grouping of real stored assessments.

Candidate correlation only: no synthetic graph links, specialist claims or
Decision severity are manufactured. Individual Evidence remains persisted.
"""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.maintenance_workflow import list_events as maintenance_events
from presentation.backend.app.environment_workflow import list_events as environmental_events

router=APIRouter()
WINDOW_SECONDS=15*60

def instant(value):
    dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Correlation requires timezone-aware original timestamps")
    return dt.astimezone(timezone.utc)

def correlate(maintenance,environment):
    pairs=[]
    for m in maintenance:
        if m["assessment"].get("assessment")!="AT_RISK":continue
        mt=instant(m["assessment"]["observation_timestamp"])
        for e in environment:
            if m["zone_id"]!=e["zone_id"]:continue
            # Match individual abnormal readings, not just the aggregate's final reading.
            history=e.get("history",[])
            states=e.get("workflow",{}).get("reading_states") or []
            for i,reading in enumerate(history):
                if i<len(states):
                    abnormal=states[i] in {"HIGH_TEMPERATURE","HIGH_HUMIDITY","LOW_HUMIDITY",
                                          "AIRFLOW_ANOMALY","SMOKE_DETECTED","WATER_LEAK_DETECTED"}
                else:
                    # Legacy batches without states are only eligible at the
                    # explicitly recorded abnormal observation timestamp.
                    abnormal=(e["assessment"].get("anomaly_detected") is True and
                              reading["timestamp"]==e["assessment"]["observation_timestamp"])
                if not abnormal:continue
                et=instant(reading["timestamp"])
                delta=abs((mt-et).total_seconds())
                if delta>WINDOW_SECONDS:continue
                pairs.append({"id":"DCG-OP-"+m["event_id"]+"-"+e["event_id"],
                  "zone_id":m["zone_id"],"maintenance_event_id":m["event_id"],
                  "environment_event_id":e["event_id"],"maintenance":m,"environment":e,
                  "time_difference_seconds":delta,"matched_environment_timestamp":reading["timestamp"],
                  "correlation_type":"CORRELATED_INFRASTRUCTURE_RISK",
                  "scope":"ZONE","status":"CORRELATION_CANDIDATE",
                  "decision":None,"decision_severity":None,
                  "explanation":"Independent abnormal maintenance and environmental assessments in the same declared zone within 15 minutes. This does not establish causation, damage, or a Decision severity."})
    # One-to-one deterministic grouping prevents duplicate feed entries for\n    # overlapping readings. Prefer closest observation-time matches.\n    chosen=[]\n    used_maintenance=set()\n    used_environment=set()\n    for pair in sorted(pairs,key=lambda x:(x["time_difference_seconds"],x["id"])):\n        if pair["maintenance_event_id"] in used_maintenance or pair["environment_event_id"] in used_environment:\n            continue\n        chosen.append(pair)\n        used_maintenance.add(pair["maintenance_event_id"])\n        used_environment.add(pair["environment_event_id"])\n    return chosen

@router.get("/api/v1/operations/correlations")
def operational_correlations(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ)
    authorize(principal,Permission.MAINTENANCE_DETAIL)
    authorize(principal,Permission.ENVIRONMENT_DETAIL)
    return correlate(maintenance_events(principal),environmental_events(principal))
