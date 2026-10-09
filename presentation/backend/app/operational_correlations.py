"""Read-only cross-session operational grouping of real stored assessments.

Candidate correlation only: no synthetic graph links, specialist claims or
Decision severity are manufactured. Individual Evidence remains persisted.
"""
from datetime import datetime,timezone
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.maintenance_workflow import list_events as maintenance_events
from presentation.backend.app.environment_workflow import list_events as environmental_events
from presentation.backend.app.graph_view import project_node
from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE

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
    # One-to-one deterministic grouping prevents duplicate feed entries for
    # overlapping readings. Prefer closest observation-time matches.
    chosen=[]
    used_maintenance=set()
    used_environment=set()
    for pair in sorted(pairs,key=lambda x:(x["time_difference_seconds"],x["id"])):
        if pair["maintenance_event_id"] in used_maintenance or pair["environment_event_id"] in used_environment:
            continue
        chosen.append(pair)
        used_maintenance.add(pair["maintenance_event_id"])
        used_environment.add(pair["environment_event_id"])
    return chosen

@router.get("/api/v1/operations/correlations")
def operational_correlations(principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.INCIDENT_READ)
    authorize(principal,Permission.MAINTENANCE_DETAIL)
    authorize(principal,Permission.ENVIRONMENT_DETAIL)
    return correlate(maintenance_events(principal),environmental_events(principal))

@router.get("/api/v1/operations/correlations/{candidate_id}/graph")
def operational_graph(candidate_id:str,principal:Principal=Depends(current_principal)):
    authorize(principal,Permission.GRAPH_READ)
    authorize(principal,Permission.MAINTENANCE_DETAIL)
    authorize(principal,Permission.ENVIRONMENT_DETAIL)
    match=next((p for p in correlate(maintenance_events(principal),environmental_events(principal))
                if p["id"]==candidate_id),None)
    if match is None:
        raise HTTPException(404,"Operational correlation candidate not found")
    zone=match["zone_id"]
    authorize(principal,Permission.GRAPH_READ,zone)
    authorize(principal,Permission.MAINTENANCE_DETAIL,zone)
    authorize(principal,Permission.ENVIRONMENT_DETAIL,zone)
    maintenance_id=match["maintenance"]["workflow"].get("graph_event_id")
    env_ids=match["environment"].get("evidence_event_ids",[])
    ids=([maintenance_id] if maintenance_id else [])+[eid+"-MAPPED" for eid in env_ids if eid.startswith("ENV-EVT-")]
    if not ids:
        raise HTTPException(409,"No mapped Neo4j Evidence event references")
    nodes={}
    edges={}
    # Directed, event-anchored paths only. Undirected traversal from shared
    # infrastructure nodes would pull in unrelated historical Event nodes.
    query="""MATCH (e:Event) WHERE e.event_id IN $ids
       OPTIONAL MATCH p=(e)-[:TARGETS]->(target)
       OPTIONAL MATCH hosted=(target)-[:HOSTED_BY]->(server:Server)
       OPTIONAL MATCH located=(server)-[:LOCATED_IN]->(rack:Rack)
       OPTIONAL MATCH rack_zone=(rack)-[:LOCATED_IN]->(zone:Zone)
       OPTIONAL MATCH sensor_zone=(target:Sensor)-[:MONITORS]->(sensor_location:Zone)
       RETURN e,p,hosted,located,rack_zone,sensor_zone
       LIMIT 100"""
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                for row in session.run(query,ids=ids):
                    event=project_node(row["e"],principal,zone)
                    nodes[event["id"]]=event
                    for key in ("p","hosted","located","rack_zone","sensor_zone"):
                        path=row[key]
                        if path is None:
                            continue
                        for node in path.nodes:
                            projected=project_node(node,principal,zone)
                            nodes[projected["id"]]=projected
                        for relation in path.relationships:
                            rid=str(relation.element_id)
                            edges[rid]={"id":rid,
                                        "source":str(relation.start_node.element_id),
                                        "target":str(relation.end_node.element_id),
                                        "type":relation.type}
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j graph unavailable") from exc
    return {"scenario_id":candidate_id,"source":"NEO4J_READ_ONLY",
            "nodes":list(nodes.values()),"edges":list(edges.values())}
