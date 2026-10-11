"""Numeric and identity claim checks across all Evidence domains.

Extends the narrow SSH checks to PPE, Face, Maintenance and Environmental
Evidence, and to every member of correlation pairs and unified groups. Same
principle: only explicitly labelled claims are compared; unrecognized wording
stays unassessed, and a missing source field is never treated as zero. A
MATCH means the number agrees with saved detector output, not that the
underlying event is real.
"""
import re
from presentation.backend.app.investigator_grounding import ssh_field_checks

NUMBER=r"(\d+(?:\.\d+)?%?|zero|one|two|three|four|five|six|seven|eight|nine|ten)"
WORDS={"zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,"ten":10}
# field -> (patterns, unit). "ratio": stored 0..1, may be claimed as a percent;
# "count": must match exactly; "value": compared at the claim's precision.
FIELDS={
 "maintenance":{
  "failure_probability":([r"\b(?:failure|risk)\s+(?:probability|score)\s*(?:is|of|was|at|=|:)?\s*(?:about\s+|approximately\s+|~)?"+NUMBER,
                          r"\b"+NUMBER+r"\s+(?:estimated\s+)?(?:failure\s+probability|failure\s+risk|risk\s+score)"],"ratio"),
  "operating_threshold":([r"\b(?:operating|alert|decision)\s+threshold\s*(?:is|of|was|at|=|:)?\s*"+NUMBER],"ratio"),
  "failure_horizon_days":([r"\b"+NUMBER+r"[- ]day\s+(?:failure\s+|prediction\s+|assessment\s+)?(?:horizon|window)",
                           r"\b(?:horizon|window)\s+of\s+"+NUMBER+r"\s+days?"],"count"),
 },
 "environment":{
  "temperature_c":([r"\btemperature\s+(?:reading\s+)?(?:is|of|was|at|reached|=|:)\s*(?:about\s+)?"+NUMBER+r"\s*°?\s*C\b"],"value"),
  "humidity_pct":([r"\bhumidity\s+(?:reading\s+)?(?:is|of|was|at|=|:)\s*(?:about\s+)?"+NUMBER],"value"),
  "temperature_high_c":([r"\b(?:high[- ]temperature|temperature)\s+threshold\s*(?:is|of|was|at|=|:)?\s*"+NUMBER+r"\s*°?\s*C?\b"],"value"),
 },
 "ppe":{
  "person_count":([r"\b"+NUMBER+r"\s+(?:persons?|people|individuals|workers)\s+(?:were\s+|was\s+)?detected",
                   r"\bdetected\s+"+NUMBER+r"\s+(?:persons?|people|individuals|workers)"],"count"),
  "non_compliant_count":([r"\b"+NUMBER+r"\s+(?:(?:persons?|people|individuals|workers)\s+(?:were\s+|was\s+|are\s+|is\s+)?)?non[- ]compliant"],"count"),
  "compliant_count":([r"\b"+NUMBER+r"\s+(?:(?:persons?|people|individuals|workers)\s+(?:were\s+|was\s+|are\s+|is\s+)?)?compliant\b"],"count"),
 },
 "face":{
  "similarity":([r"\bsimilarity\s*(?:score)?\s*(?:is|of|was|=|:)?\s*"+NUMBER],"ratio"),
  "distance":([r"\b(?:cosine\s+)?distance\s*(?:is|of|was|=|:)\s*"+NUMBER],"ratio"),
  "threshold":([r"\b(?:recognition|distance|matching|match)\s+threshold\s*(?:is|of|was|=|:)?\s*"+NUMBER],"ratio"),
 },
}
# Frozen field names are valid explicit labels ("temperature_c: 38.0").
for _domain in FIELDS.values():
    for _field,(_patterns,_unit) in _domain.items():
        _patterns.append(r"\b"+re.escape(_field)+r"\s*[:=]\s*(\d+(?:\.\d+)?%?)(?![\d.])")
FIELDS={d:{f:([re.compile(p,re.I) for p in ps],u) for f,(ps,u) in fs.items()} for d,fs in FIELDS.items()}
PERSON_ID=re.compile(r"\bP\d{3}\b")

def find(record,field,depth=0):
    """First scalar value for a field anywhere in the allowlisted record."""
    if not isinstance(record,dict) or depth>4:return None
    if field in record and not isinstance(record[field],(dict,list)):return record[field]
    for value in record.values():
        found=find(value,field,depth+1)
        if found is not None:return found
    return None

def find_list(record,field,depth=0):
    if not isinstance(record,dict) or depth>4:return None
    if isinstance(record.get(field),list):return record[field]
    for value in record.values():
        found=find_list(value,field,depth+1)
        if found is not None:return found
    return None

def source_value(kind,record,field):
    if kind=="ppe" and field in ("person_count","non_compliant_count","compliant_count"):
        people=find_list(record,"people")
        if field=="person_count":
            count=find(record,"person_count")
            return count if count is not None else (len(people) if people is not None else None)
        if people is None:return None
        wanted="NON_COMPLIANT" if field=="non_compliant_count" else "COMPLIANT"
        return sum(1 for p in people if isinstance(p,dict) and p.get("status")==wanted)
    return find(record,field)

def compare(raw,actual,unit):
    """MATCH within the claim's stated precision; counts must be exact."""
    if isinstance(actual,bool) or actual is None:return "SOURCE_FIELD_UNAVAILABLE"
    try:actual=float(actual)
    except (TypeError,ValueError):return "SOURCE_FIELD_UNAVAILABLE"
    raw=raw.lower()
    percent=raw.endswith("%")
    number=raw.rstrip("%")
    claimed=float(WORDS[number]) if number in WORDS else float(number)
    decimals=len(number.split(".")[1]) if "." in number else 0
    value=actual*100 if unit=="ratio" and (percent or claimed>1) else actual
    if unit=="count":
        return "MATCH" if abs(value-claimed)<1e-9 else "MISMATCH"
    # One unit in the last stated digit allows rounding or truncation.
    tolerance=10**-decimals if decimals else 0.5
    return "MATCH" if abs(value-claimed)<=tolerance+1e-9 else "MISMATCH"

def domain_field_checks(kind,answer,record,evidence_id=None):
    checks=[]
    normalized=answer.replace("**","").replace("`","")
    for field,(patterns,unit) in FIELDS.get(kind,{}).items():
        expected=source_value(kind,record,field)
        seen=set()
        # Each line separately, so a label never takes a number from the next line.
        for line_number,line in enumerate(normalized.splitlines()):
            for pattern in patterns:
                for match in pattern.finditer(line):
                    span=(line_number,)+match.span(1)
                    if span in seen:continue
                    seen.add(span)
                    checks.append({"domain":kind,"evidence_id":evidence_id,"field":field,
                                   "claim":match.group(0),"source_value":expected,
                                   "status":compare(match.group(1),expected,unit)})
    return checks

def identity_checks(answer,records):
    """Person IDs in the answer must belong to a Face record in the context."""
    allowed=set()
    for kind,_,record in records:
        if kind=="face":
            for key in ("person_id","nearest_employee_id"):
                value=find(record,key)
                if isinstance(value,str) and value!="UNKNOWN":allowed.add(value)
    return [{"domain":"face","evidence_id":None,"field":"person_id","claim":person,
             "source_value":sorted(allowed) or None,
             "status":"MATCH" if person in allowed else "MISMATCH"}
            for person in sorted(set(PERSON_ID.findall(answer)))]

def summarize(checks,skipped=()):
    status=("MISMATCH" if any(c["status"]=="MISMATCH" for c in checks)
            else "PARTIAL_FIELD_CHECK" if checks else "NO_RECOGNIZED_CLAIMS")
    return {"status":status,"checks":checks,"skipped":list(skipped),
            "summary":{"matched":sum(c["status"]=="MATCH" for c in checks),
                       "mismatched":sum(c["status"]=="MISMATCH" for c in checks),
                       "source_unavailable":sum(c["status"]=="SOURCE_FIELD_UNAVAILABLE" for c in checks),
                       "recognized":len(checks)},
            "note":"Only recognized numeric and person-ID claims were compared with saved detector fields; other claims remain unverified."}

def context_field_checks(answer,records):
    """records: (kind, evidence_id, saved record) for every Evidence in context.

    A domain with several members is skipped: a bare number cannot be
    attributed to one of them without guessing.
    """
    checks=[];skipped=[]
    by_kind={}
    for kind,evidence_id,record in records:
        by_kind.setdefault(kind,[]).append((evidence_id,record))
    for kind,items in sorted(by_kind.items()):
        if len(items)>1:
            skipped.append({"domain":kind,"reason":"AMBIGUOUS_MULTIPLE_MEMBERS","count":len(items)})
            continue
        evidence_id,record=items[0]
        if kind=="ssh":
            checks.extend({"domain":"ssh","evidence_id":evidence_id,**c}
                          for c in ssh_field_checks(answer,record)["checks"])
        else:
            checks.extend(domain_field_checks(kind,answer,record,evidence_id))
    checks.extend(identity_checks(answer,records))
    return summarize(checks,skipped)
