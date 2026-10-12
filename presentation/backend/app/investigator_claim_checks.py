"""Sentence-level checks of Investigator explanations against the Evidence.

Complements investigator_field_checks (numbers, person IDs) with two claim types:

1. Boundary claims. Every Investigator context states that causation, identity
   links, physical presence and compromise are NOT established and that no
   autonomous action is allowed. An affirmative claim of any of these is a
   VIOLATION. A negated claim ("does not prove it caused") is NEGATED (fine);
   a hedged one ("may have contributed") is HEDGED: speculation the operator
   should read as such.
2. State claims. Wording such as "compliant", "at risk", "unauthorized" or
   "benign" is compared with the detector state and any human verdict of the
   single record of that domain in context (a domain with several members is
   skipped, as for numbers). Matching the human status counts as a match.

Deterministic and pattern-based: unrecognized wording stays unassessed, so a
clean result means "no recognized problem", not "verified".
"""
import re

SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
NEGATION = re.compile(r"\b(?:not|no|never|cannot|can't|without|neither|nor|unproven|unverified|unconfirmed|"
                      r"doesn't|don't|isn't|aren't|wasn't|weren't|didn't|hasn't|haven't|insufficient|lack|lacks|"
                      r"absence|rather than|instead of|unable)\b", re.I)
HEDGE = re.compile(r"\b(?:may|might|could|possibly|possible|potential(?:ly)?|perhaps|likely|suggests?|"
                   r"consistent with|cannot rule out|warrants?|worth (?:checking|investigating))\b", re.I)

BOUNDARIES = {
    "CAUSATION": re.compile(r"\b(?:caused|causes|causing|led to|leads to|resulted in|results in|root cause|"
                            r"is (?:the )?(?:reason|result) (?:for|of)|triggered by|because of the)\b", re.I),
    "IDENTITY": re.compile(r"\b(?:P\d{3,8}|the (?:recognized|identified) (?:person|employee))\s+"
                           r"(?:logged in|accessed|performed|carried out|initiated|was responsible|is responsible|"
                           r"attempted|attacked|ran|executed)\b|\b(?:identity (?:is|was) (?:confirmed|established)|"
                           r"same person)\b", re.I),
    # Includes wording seen in live answers (2026-10-12): "indicating physical presence",
    # "detected inside the server hall".
    "PHYSICAL_PRESENCE": re.compile(r"\b(?:was|is|were) physically (?:present|in)|\bphysically entered\b|"
                                    r"\bphysical presence\b|"
                                    r"\b(?:entered|was inside|was present in|were inside|is inside) (?:the )?(?:server )?(?:hall|room|zone)\b|"
                                    r"\b(?:detected|seen|captured|recognized) inside (?:the )?(?:server )?(?:hall|room)\b", re.I),
    "COMPROMISE": re.compile(r"\b(?:was|is|has been|were) (?:compromised|breached|hacked)\b|"
                             r"\b(?:confirmed|successful) (?:compromise|breach|intrusion|attack)\b", re.I),
    "AUTONOMOUS_ACTION": re.compile(r"\b(?:I|we|the system) (?:have |has )?(?:locked|blocked|disabled|shut down|"
                                    r"isolated|quarantined|revoked)\b|\bhas been (?:automatically )?(?:locked|blocked|"
                                    r"disabled|isolated|quarantined)\b", re.I),
}

# Domain -> list of (pattern, canonical state). Order matters: negative forms first.
STATES = {
    "ppe": [(r"\bnon[- ]?compliant\b|\bnot compliant\b|\bmissing (?:required )?(?:ppe|vest|helmet)s?\b(?!\W*(?:none|nothing|n/a)\b)", "NON_COMPLIANT"),
            (r"\bcompliant\b|\bfully equipped\b", "COMPLIANT")],
    "maintenance": [(r"\bat[- ]risk\b|\blikely to fail\b", "AT_RISK"),
                    (r"\b(?:drive|disk) (?:is |was )?(?:healthy|normal)\b|\bhealthy drive\b", "HEALTHY")],
    "face": [(r"\bunauthori[sz]ed\b|\bnot authori[sz]ed\b", "UNAUTHORIZED"),
             (r"\bunknown person\b|\bunrecogni[sz]ed\b|\bnot recogni[sz]ed\b", "UNKNOWN_PERSON"),
             (r"\b(?:is|was) authori[sz]ed\b", "AUTHORIZED")],
    # Claim-like wording only: "is benign", "looks benign", "benign activity" (not "its benign nature").
    "ssh": [(r"\b(?:is|was|are|were|appears?|looks?|seems?)(?: to be)? (?:likely |probably )?benign\b|"
             r"\bbenign (?:activity|traffic|login|event)s?\b|\bno anomal(?:y|ies)\b|\bnormal (?:ssh )?activity\b", "BENIGN"),
            (r"\banomal(?:y|ous|ies)\b|\bbrute[- ]force\b|\bsuspicious\b", "ANOMALOUS")],
    "environment": [(r"\bhigh temperature\b|\boverheat|\btemperature (?:is |was )?(?:too )?high\b|"
                     r"\babnormal (?:temperature|humidity|reading)", "ABNORMAL"),
                    (r"\b(?:temperature|readings?|conditions?) (?:is |are |was |were )?(?:normal|within (?:the )?(?:normal )?range)\b", "NORMAL")],
}
STATES = {k: [(re.compile(p, re.I), s) for p, s in v] for k, v in STATES.items()}
# Detector/human vocabulary -> the canonical states above.
CANONICAL = {
    "ppe": {"NON_COMPLIANT": "NON_COMPLIANT", "PPE_NON_COMPLIANT": "NON_COMPLIANT", "COMPLIANT": "COMPLIANT"},
    "maintenance": {"AT_RISK": "AT_RISK", "HEALTHY": "HEALTHY", "NORMAL": "HEALTHY"},
    "face": {"UNAUTHORIZED": "UNAUTHORIZED", "UNKNOWN_PERSON": "UNKNOWN_PERSON", "AUTHORIZED": "AUTHORIZED"},
    "ssh": {"HIGH_CONFIDENCE_ANOMALY": "ANOMALOUS", "ANOMALY_CANDIDATE": "ANOMALOUS",
            "EXPLICIT_SECURITY_EVENT": "ANOMALOUS", "ANOMALOUS": "ANOMALOUS",
            "NO_ANOMALY_EVIDENCE": "BENIGN", "BENIGN": "BENIGN"},
    "environment": {"NORMAL": "NORMAL", "ABNORMAL": "ABNORMAL"},
}


def sentences(answer):
    return [s.strip() for s in SENTENCE.split(answer or "") if s.strip()]


HEADING = re.compile(r"^\s*#")
STARTS_NEGATED = re.compile(r"^(?:not|no|non|un)", re.I)


def negated_just_before(sentence, start):
    """A negator among the three words right before the match ("not clearly benign")."""
    return bool(NEGATION.search(" ".join(sentence[:start].split()[-3:])))


def boundary_checks(answer):
    checks = []
    for sentence in sentences(answer):
        for boundary, pattern in BOUNDARIES.items():
            match = pattern.search(sentence)
            if not match:
                continue
            before = sentence[:match.start()]
            status = ("NEGATED" if NEGATION.search(before) or NEGATION.search(sentence[match.end():match.end() + 25])
                      else "HEDGED" if HEDGE.search(sentence) else "VIOLATION")
            checks.append({"type": "BOUNDARY", "boundary": boundary, "sentence": sentence, "status": status})
    return checks


def _find(record, keys, depth=0):
    if not isinstance(record, dict) or depth > 4:
        return None
    for key in keys:
        if isinstance(record.get(key), str):
            return record[key]
    for value in record.values():
        found = _find(value, keys, depth + 1)
        if found:
            return found
    return None


def record_states(kind, record):
    """Canonical detector state and human status of one saved record."""
    keys = {"ppe": ("overall_status", "status"), "maintenance": ("assessment",),
            "face": ("recognition_status",), "ssh": ("evidence_state",), "environment": ("assessment",)}[kind]
    detector = _find(record, keys)
    if kind == "face":
        auth = _find(record.get("zone_authorization") or {}, ("status",)) if isinstance(record, dict) else None
        if auth in ("UNAUTHORIZED", "AUTHORIZED") and detector == "RECOGNIZED":
            detector = auth
    if kind == "environment" and detector and detector != "NORMAL":
        detector = "ABNORMAL"
    human = (record.get("human_review") or {}).get("effective_status") if isinstance(record, dict) else None
    canon = CANONICAL[kind]
    return canon.get(detector or ""), canon.get(human or "")


def person_states(record):
    """Per-person PPE statuses: a sentence about one worker may state that worker's status."""
    people = _find_list(record, "people") or []
    return {CANONICAL["ppe"].get(p.get("status") or "") for p in people if isinstance(p, dict)} - {None}


def _find_list(record, key, depth=0):
    if not isinstance(record, dict) or depth > 4:
        return None
    if isinstance(record.get(key), list):
        return record[key]
    for value in record.values():
        found = _find_list(value, key, depth + 1)
        if found is not None:
            return found
    return None


def state_checks(answer, records):
    by_kind, skipped, checks = {}, [], []
    for kind, evidence_id, record in records:
        if kind in STATES:
            by_kind.setdefault(kind, []).append((evidence_id, record))
    for kind, items in sorted(by_kind.items()):
        if len(items) > 1:
            skipped.append({"domain": kind, "reason": "AMBIGUOUS_MULTIPLE_MEMBERS", "count": len(items)})
            continue
        evidence_id, record = items[0]
        detector, human = record_states(kind, record)
        if detector is None and human is None:
            continue
        per_person = person_states(record) if kind == "ppe" else set()
        for sentence in sentences(answer):
            if HEADING.match(sentence):
                continue  # a heading ("### Missing PPE") labels a section; it states nothing
            for pattern, claimed in STATES[kind]:
                match = pattern.search(sentence)
                if not match:
                    continue
                if not STARTS_NEGATED.match(match.group(0)) and negated_just_before(sentence, match.start()):
                    break  # "not at risk", "not clearly benign": a negated claim; leave unassessed
                status = ("MATCH" if claimed in (detector, human) or claimed in per_person else "MISMATCH")
                checks.append({"type": "STATE", "domain": kind, "evidence_id": evidence_id, "sentence": sentence,
                               "claimed": claimed, "detector_state": detector, "human_status": human, "status": status})
                break  # first (most specific) pattern per sentence
    return checks, skipped


def claim_checks(answer, records):
    """records: (kind, evidence_id, saved record incl. human_review) for every Evidence in context."""
    boundaries = boundary_checks(answer)
    states, skipped = state_checks(answer, records)
    checks = boundaries + states
    status = ("VIOLATION" if any(c["status"] == "VIOLATION" for c in boundaries)
              else "MISMATCH" if any(c["status"] == "MISMATCH" for c in states)
              else "HEDGED" if any(c["status"] == "HEDGED" for c in boundaries)
              else "NO_RECOGNIZED_PROBLEM")
    return {"status": status, "checks": checks, "skipped": skipped,
            "summary": {"violations": sum(c["status"] == "VIOLATION" for c in checks),
                        "hedged": sum(c["status"] == "HEDGED" for c in checks),
                        "state_mismatches": sum(c.get("type") == "STATE" and c["status"] == "MISMATCH" for c in checks),
                        "state_matches": sum(c.get("type") == "STATE" and c["status"] == "MATCH" for c in checks)},
            "note": "Pattern-based sentence checks: causal, identity, presence, compromise and action claims, and "
                    "detector-state wording. Unrecognized wording is not assessed."}
