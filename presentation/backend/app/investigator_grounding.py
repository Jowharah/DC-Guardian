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
# Recognize only explicit count/ratio claims; do not infer unstated values.
# Each pattern captures the numeric value in group 1.
SSH_PATTERNS={
 "failed_login_count":[
  r"\b(\d+)\s+failed\s+(?:SSH\s+)?login\s+attempts?\b",
  r"\bfailed\s+login\s+count\s*[:=]\s*(\d+)\b"],
 "invalid_user_count":[r"\binvalid\s+user\s+count\s*[:=]\s*(\d+)\b"],
 "unique_users":[r"\bunique\s+users?\s+(?:attempted\s*)?[:=]\s*(\d+)\b"],
 "detector_votes":[r"\b(\d+)\s+(?:detector|component)\s+votes?\b",
                   r"\bdetector\s+votes?\s*(?:count\s*)?[:=]\s*(\d+)\b"],
 "successful_login_count":[r"\b(\d+)\s+successful\s+logins?\b",
                           r"\bsuccessful\s+login\s+count\s*[:=]\s*(\d+)\b"],
 "failure_ratio":[r"\bfailure\s+ratio\s*(?:is|of|=|:)\s*(\d+(?:\.\d+)?%?)"],
 "root_attempt_ratio":[r"\broot\s+attempt\s+ratio\s*(?:is|of|=|:)\s*(\d+(?:\.\d+)?%?)"],
 "breakin_warning_count":[r"\bbreak[- ]in\s+warning\s+count\s*[:=]\s*(\d+)\b"],
 "disconnect_count":[r"\bdisconnect\s+count\s*[:=]\s*(\d+)\b"],
 "no_identification_count":[r"\bno\s+identification\s+count\s*[:=]\s*(\d+)\b"],
 "success_after_failures":[r"\bsuccess\s+after\s+failures\s+count\s*[:=]\s*(\d+)\b"],
}
SSH_PATTERNS={key:[re.compile(p,re.I) for p in patterns] for key,patterns in SSH_PATTERNS.items()}

def ssh_field_checks(answer:str,assessment:dict)->dict:
    if not isinstance(assessment,dict):
        return {"status":"NO_STRUCTURED_SOURCE","checks":[],"note":"No structured assessment supplied."}
    evidence=assessment.get("evidence")
    evidence=evidence if isinstance(evidence,dict) else {}
    # Published SSH assessments carry frozen metrics in evidence; some
    # adapters nest them under evidence.metrics. Never default missing to zero.
    nested=evidence.get("metrics")
    nested=nested if isinstance(nested,dict) else {}
    top=assessment.get("metrics")
    top=top if isinstance(top,dict) else {}
    checks=[]
    for field,patterns in SSH_PATTERNS.items():
        expected=next((d[field] for d in (assessment,top,evidence,nested) if field in d),None)
        found=[]
        for pattern in patterns:
            for match in pattern.finditer(answer):
                if any(match.start()<end and match.end()>begin for begin,end in found):
                    continue
                found.append(match.span())
                raw=match.group(1)
                try:
                    claimed=float(raw.rstrip("%"))
                    if raw.endswith("%"):claimed/=100
                    if isinstance(expected,bool) or expected is None:
                        status="SOURCE_FIELD_UNAVAILABLE"
                    else:
                        actual=float(expected)
                        status="MATCH" if abs(claimed-actual)<1e-9 else "MISMATCH"
                except (TypeError,ValueError,OverflowError):
                    status="SOURCE_FIELD_UNAVAILABLE"
                checks.append({"field":field,"claim":match.group(0),
                               "source_value":expected,"status":status})
                if len(found)>=5:break
    status=("MISMATCH" if any(c["status"]=="MISMATCH" for c in checks)
            else "PARTIAL_FIELD_CHECK" if checks
            else "NO_RECOGNIZED_CLAIMS")
    return {"status":status,"checks":checks,
            "note":"Only recognized numeric phrases were compared with saved detector fields; other claims remain unverified."}
