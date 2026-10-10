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

# Narrow, deterministic SSH numeric claim checks. Unsupported phrasing is
# deliberately left unassessed rather than being marked verified.
SSH_PATTERNS={
 "failed_login_count":re.compile(r"\b(\d+)\s+failed\s+(?:SSH\s+)?login\s+attempts?\b",re.I),
 "detector_votes":re.compile(r"\b(\d+)\s+(?:detector|component)\s+votes?\b",re.I),
 "successful_login_count":re.compile(r"\b(\d+)\s+successful\s+logins?\b",re.I),
 "failure_ratio":re.compile(r"\bfailure\s+ratio\s*(?:is|of|=|:)\s*(\d+(?:\.\d+)?%?)",re.I),
 "root_attempt_ratio":re.compile(r"\broot\s+attempt\s+ratio\s*(?:is|of|=|:)\s*(\d+(?:\.\d+)?%?)",re.I),
}
def ssh_field_checks(answer:str,assessment:dict)->dict:
    if not isinstance(assessment,dict):return {"status":"NO_STRUCTURED_SOURCE","checks":[]}
    metrics=assessment.get("metrics")
    if not isinstance(metrics,dict):
        evidence=assessment.get("evidence")
        metrics=evidence.get("metrics") if isinstance(evidence,dict) else None
    metrics=metrics if isinstance(metrics,dict) else {}
    checks=[]
    for field,pattern in SSH_PATTERNS.items():
        expected=assessment.get(field) if field=="detector_votes" else metrics.get(field)
        for match in list(pattern.finditer(answer))[:5]:
            raw=match.group(1)
            try:
                claimed=float(raw.rstrip("%"))
                if raw.endswith("%"):claimed/=100
                actual=float(expected)
                status="MATCH" if abs(claimed-actual)<1e-9 else "MISMATCH"
            except (ValueError,TypeError):
                status="SOURCE_FIELD_UNAVAILABLE"
            checks.append({"field":field,"claim":match.group(0),"source_value":expected,
                           "status":status})
    status="MISMATCH" if any(c["status"]=="MISMATCH" for c in checks) else (
        "PARTIAL_FIELD_CHECK" if checks else "NO_RECOGNIZED_CLAIMS")
    return {"status":status,"checks":checks,
            "note":"Only recognized numeric phrases were compared with saved detector fields; other claims remain unverified."}
