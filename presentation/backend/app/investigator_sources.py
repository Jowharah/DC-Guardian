"""Deterministic source-reference manifest, independent of model prose.

References are returned from authorized investigation context. Presence in the
manifest does not prove that every generated claim is supported.
"""
def unified_sources(context):
    return [{"kind":ref["kind"],"id":ref["observation_id"],"role":"saved_source_evidence"}
            for ref in context.get("evidence_refs",[])
            if ref.get("kind") and ref.get("observation_id")]

def operational_sources(context):
    result=[]
    for kind in ("maintenance","environment"):
        item=context.get(kind) or {}
        if item.get("event_id"):
            result.append({"kind":kind,"id":item["event_id"],"role":"saved_source_evidence"})
    for evidence_id in context.get("evidence_event_ids",[]):
        if isinstance(evidence_id,str) and not any(x["id"]==evidence_id for x in result):
            result.append({"kind":"graph","id":evidence_id,"role":"saved_graph_evidence"})
    return result

def single_sources(context):
    return [{"kind":context["kind"],"id":context["evidence_id"],"role":"saved_source_evidence"}]
