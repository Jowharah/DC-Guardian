"""Bounded read-only Neo4j investigation for stored standalone Evidence."""
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.maintenance_workflow import list_events as maintenance_events
from presentation.backend.app.environment_workflow import list_events as environmental_events
from presentation.backend.app.ssh_publication import connect as ssh_connect
from presentation.backend.app.graph_view import project_node
from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE

router=APIRouter()
PERMISSIONS={"ssh":Permission.SSH_DETAIL,"maintenance":Permission.MAINTENANCE_DETAIL,
             "environment":Permission.ENVIRONMENT_DETAIL}

def resolve(kind,event_id,principal):
    if kind=="maintenance":
        record=next((x for x in maintenance_events(principal) if x["event_id"]==event_id),None)
        if record is None:raise HTTPException(404,"Maintenance evidence not found")
        graph_id=record["workflow"].get("graph_event_id")
        ids=[graph_id] if graph_id else []
    elif kind=="environment":
        record=next((x for x in environmental_events(principal) if x["event_id"]==event_id),None)
        if record is None:raise HTTPException(404,"Environmental evidence not found")
        ids=[x+"-MAPPED" for x in record.get("evidence_event_ids",[])
             if x.startswith("ENV-EVT-")]
    else:
        with ssh_connect() as db:
            row=db.execute("SELECT zone_id FROM ssh_published_evidence WHERE event_id=?",
                           (event_id,)).fetchone()
        if row is None:raise HTTPException(404,"SSH evidence not found")
        record={"zone_id":row[0]}
        ids=[event_id+"-MAPPED"]
    return record["zone_id"],ids

def read_graph(ids,principal,zone,reference):
    if not ids:raise HTTPException(409,"No mapped Evidence event references")
    # Directed, bounded paths prevent traversal into unrelated historical events.
    query="""MATCH (e:Event) WHERE e.event_id IN $ids
       OPTIONAL MATCH p=(e)-[:TARGETS]->(target)
       OPTIONAL MATCH hosted=(target)-[:HOSTED_BY]->(server:Server)
       OPTIONAL MATCH located=(server)-[:LOCATED_IN]->(rack:Rack)
       OPTIONAL MATCH rack_zone=(rack)-[:LOCATED_IN]->(zone:Zone)
       OPTIONAL MATCH sensor_zone=(target:Sensor)-[:MONITORS]->(sensor_location:Zone)
       OPTIONAL MATCH server_rack=(target:Server)-[:LOCATED_IN]->(direct_rack:Rack)
       OPTIONAL MATCH direct_zone=(direct_rack)-[:LOCATED_IN]->(direct_zone_node:Zone)
       RETURN e,p,hosted,located,rack_zone,sensor_zone,server_rack,direct_zone
       LIMIT 120"""
    nodes={};edges={}
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                for row in session.run(query,ids=ids):
                    event=project_node(row["e"],principal,zone)
                    nodes[event["id"]]=event
                    for key in ("p","hosted","located","rack_zone","sensor_zone","server_rack","direct_zone"):
                        path=row[key]
                        if path is None:continue
                        for node in path.nodes:
                            projected=project_node(node,principal,zone)
                            nodes[projected["id"]]=projected
                        for relation in path.relationships:
                            rid=str(relation.element_id)
                            edges[rid]={"id":rid,"source":str(relation.start_node.element_id),
                                        "target":str(relation.end_node.element_id),
                                        "type":relation.type}
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j graph unavailable") from exc
    if not nodes:raise HTTPException(404,"Mapped Evidence not present in Neo4j")
    return {"scenario_id":reference,"source":"NEO4J_READ_ONLY",
            "nodes":list(nodes.values()),"edges":list(edges.values())}

@router.get("/api/v1/evidence/{kind}/{event_id}/graph")
def standalone_graph(kind:str,event_id:str,principal:Principal=Depends(current_principal)):
    if kind not in PERMISSIONS:raise HTTPException(404,"Unknown Evidence domain")
    authorize(principal,Permission.GRAPH_READ)
    authorize(principal,PERMISSIONS[kind])
    zone,ids=resolve(kind,event_id,principal)
    authorize(principal,Permission.GRAPH_READ,zone)
    authorize(principal,PERMISSIONS[kind],zone)
    return read_graph(ids,principal,zone,event_id)
