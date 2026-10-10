"""Conservative deterministic checks for Investigator answer provenance.

Checks explicit Evidence identifiers only. This is not semantic claim verification.
"""
import re

ID_PATTERN=re.compile(r"\b(?:SSH-EVT|PPE-IMG|FACE-IMG|MAINT-EVT|ENV-BATCH|ENV-EVT)-[A-Z0-9-]+\b",re.I)

def check_answer_references(answer:str,sources:list[dict])->dict:
    allowed={str(source["id"]).upper() for source in sources if source.get("id")}
    mentioned=set(match.group(0).upper() for match in ID_PATTERN.finditer(answer))
    unknown=sorted(mentioned-allowed)
    supported=sorted(mentioned & allowed)
    return {
        "status":"UNVERIFIED_REFERENCES" if unknown else "REFERENCE_CHECK_ONLY",
        "referenced_ids":supported,
        "unrecognized_ids":unknown,
        "claim_validation":"NOT_PERFORMED",
        "note":"Matching a source ID does not verify numerical, causal, identity, or other narrative claims."
    }
