"""Bounded, read-only Neo4j graph for a validated unified candidate.

Only selected Evidence event IDs are anchors. No synthetic correlation edges,
unbounded neighbor traversal, or unrelated historical Events are included.
"""
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.unified_correlations import unified_correlations
from presentation.backend.app.graph_view import project_node
from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE

router=APIRouter()
REQUIRED=(Permission.INCIDENT_READ,Permission.GRAPH_READ,Permission.SSH_DETAIL,
          Permission.MAINTENANCE_DETAIL,Permission.ENVIRONMENT_DETAIL,
          Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL)

def graph_ids(group,principal):
    """Resolve original source IDs to existing mapped graph IDs."""
    from presentation.backend.app.maintenance_workflow import list_events
    from presentation.backend.app.environment_workflow import list_events as environment_events
    maintenance={x["event_id"]:x for x in list_events(principal)}
    environment={x["event_id"]:x for x in environment_events(principal)}
    ids=[]
    for ref in group["evidence"]:
        kind=ref["kind"];oid=ref["observation_id"]
        if kind in ("ppe","face"):
            ids.append("IMG-EVT-"+oid)
        elif kind=="ssh":
            ids.append(oid+"-MAPPED")
        elif kind=="maintenance":
            event=maintenance.get(oid)
            graph_id=event.get("workflow",{}).get("graph_event_id") if event else None
            if not graph_id:raise HTTPException(409,"Maintenance graph reference unavailable")
            ids.append(graph_id)
        elif kind=="environment":
            event=environment.get(oid)
            graph_refs=event.get("evidence_event_ids",[]) if event else []
            if not graph_refs:raise HTTPException(409,"Environmental graph references unavailable")
            ids.extend(x+"-MAPPED" for x in graph_refs if x.startswith("ENV-EVT-"))
        else:
            raise HTTPException(409,"Unknown Evidence domain")
    return sorted(set(ids))

@router.get("/api/v1/correlations/unified/{group_id}/graph")
def unified_graph(group_id:str,principal:Principal=Depends(current_principal)):
    for perm in REQUIRED:authorize(principal,perm)
    group=next((g for g in unified_correlations(principal) if g["id"]==group_id),None)
    if group is None:raise HTTPException(404,"Unified correlation group not found")
    for perm in REQUIRED:authorize(principal,perm,group["zone_id"])
    ids=graph_ids(group,principal)
    if len(ids)>40:raise HTTPException(409,"Graph exceeds bounded Evidence limit")
    query="""MATCH (e:Event) WHERE e.event_id IN $ids
       OPTIONAL MATCH p=(e)-[r]->(n)
       WHERE type(r) IN ['OBSERVED_BY','TARGETS','ORIGINATED_FROM','DETECTED_AT']
         AND NOT n:Event
       RETURN e,p LIMIT 160"""
    nodes={};edges={};found=set()
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                for row in session.run(query,ids=ids):
                    e=row["e"]
                    found.add(e["event_id"])
                    projected=project_node(e,principal,group["zone_id"])
                    nodes[projected["id"]]=projected
                    path=row["p"]
                    if path is None:continue
                    for node in path.nodes:
                        p=project_node(node,principal,group["zone_id"])
                        nodes[p["id"]]=p
                    for rel in path.relationships:
                        rid=str(rel.element_id)
                        edges[rid]={"id":rid,"source":str(rel.start_node.element_id),
                                    "target":str(rel.end_node.element_id),"type":rel.type}
                # Separate verified authorization context; never join Person to
                # camera, PPE detections, or SSH based on a contextual candidate.
                from presentation.backend.app import face_observations
                recognized=set()
                for ref in group["evidence"]:
                    if ref["kind"]!="face":continue
                    record=face_observations.get(ref["observation_id"])
                    if not record:continue
                    assessment=record.get("assessment",{})
                    if assessment.get("recognition_status")=="RECOGNIZED" and assessment.get("person_id"):
                        recognized.add(assessment["person_id"])
                if recognized:
                    auth_query="""MATCH (p:Person)-[r:AUTHORIZED_FOR]->(z:Zone {zone_id:$zone})
                        WHERE p.person_id IN $people
                        RETURN p,r,z LIMIT 30"""
                    for row in session.run(auth_query,zone=group["zone_id"],people=sorted(recognized)):
                        for node in (row["p"],row["z"]):
                            projected=project_node(node,principal,group["zone_id"])
                            nodes[projected["id"]]=projected
                        rel=row["r"]
                        rid=str(rel.element_id)
                        edges[rid]={"id":rid,"source":str(rel.start_node.element_id),
                                    "target":str(rel.end_node.element_id),"type":rel.type}
        finally:driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j graph unavailable") from exc
    if set(ids)!=found:
        raise HTTPException(409,"Unified graph Evidence nodes missing")
    return {"scenario_id":group_id,"source":"NEO4J_READ_ONLY",
            "nodes":list(nodes.values()),"edges":list(edges.values()),
            "evidence_count":len(ids),"verified_event_count":len(found)}
