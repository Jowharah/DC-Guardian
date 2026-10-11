"""Read-only selected PPE/Face event and declared camera graph."""
from fastapi import APIRouter,Depends,HTTPException
from presentation.backend.app.authentication import current_principal,authorize
from presentation.backend.app.authorization import Principal,Permission
from presentation.backend.app.physical_image_correlations import image_correlations
from presentation.backend.app.graph_view import project_node
from reasoning.graph.ingest_event import create_driver,NEO4J_DATABASE

router=APIRouter()

@router.get("/api/v1/physical/image-correlations/{candidate_id}/graph")
def physical_graph(candidate_id:str,principal:Principal=Depends(current_principal)):
    for permission in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL,Permission.GRAPH_READ):
        authorize(principal,permission)
    candidate=next((c for c in image_correlations(principal) if c["id"]==candidate_id),None)
    if candidate is None:
        raise HTTPException(404,"Physical image correlation candidate not found")
    zone=candidate["zone_id"]
    for permission in (Permission.CAMERA_DETAIL,Permission.PERSON_DETAIL,Permission.GRAPH_READ):
        authorize(principal,permission,zone)
    ids=["IMG-EVT-"+candidate["ppe_observation_id"],
         "IMG-EVT-"+candidate["face_observation_id"]]
    query="""MATCH (e:Event) WHERE e.event_id IN $ids
      OPTIONAL MATCH p=(e)-[:OBSERVED_BY]->(camera:Camera)
      RETURN e,p LIMIT 12"""
    nodes={};edges={}
    try:
        driver=create_driver()
        try:
            with driver.session(database=NEO4J_DATABASE,default_access_mode="READ") as session:
                for row in session.run(query,ids=ids):
                    event=project_node(row["e"],principal,zone)
                    nodes[event["id"]]=event
                    path=row["p"]
                    if path is None:continue
                    for node in path.nodes:
                        projected=project_node(node,principal,zone)
                        nodes[projected["id"]]=projected
                    for rel in path.relationships:
                        rid=str(rel.element_id)
                        edges[rid]={"id":rid,"source":str(rel.start_node.element_id),
                                    "target":str(rel.end_node.element_id),"type":rel.type}
        finally:
            driver.close()
    except Exception as exc:
        raise HTTPException(503,"Neo4j graph unavailable") from exc
    if sum(n["type"]=="Event" for n in nodes.values())!=2:
        raise HTTPException(409,"Both mapped image Evidence events must exist")
    return {"scenario_id":candidate_id,"source":"NEO4J_READ_ONLY",
            "nodes":list(nodes.values()),"edges":list(edges.values())}
