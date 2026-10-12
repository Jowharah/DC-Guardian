"""Access matrix: every API operation, every role.

Each operation in the OpenAPI schema must appear in POLICY, which states who
may pass its authorization. The test calls every operation as every non-admin
role with a schema-valid request and dummy IDs, and checks:

- without credentials every operation except /health answers 401;
- a role lacking the required permission gets 403 (refused before any lookup),
  except operations marked LOOKUP, which filter by permission while looking the
  resource up and so answer 404 for an unknown ID;
- a role holding the permission is not refused (its answer is then 404/409/422
  for the dummy IDs, never 401/403).

A new endpoint fails `test_every_operation_is_classified` until it is added to
POLICY, so its access rule is reviewed on purpose. Runs with a throw-away
database, an unreachable Neo4j and OpenAI blocked: nothing real is touched.
Zone isolation with real records is covered by the domain RBAC tests
(test_domain_feed_http_rbac, test_image_http_rbac, test_review_http_rbac, ...).
"""
import re

import pytest
from fastapi.testclient import TestClient

from presentation.backend.app.authentication import current_principal
from presentation.backend.app.authorization import ROLE_PERMISSIONS, Principal
from presentation.backend.app.main import app

KINDS = ("ssh", "ppe", "face", "maintenance", "environment")
ROLES = tuple(r for r in ROLE_PERMISSIONS if r != "administrator")
ALL_ZONES = frozenset({"ZONE-A", "ZONE-B", "ZONE-C"})

# Who may pass authorization (besides administrators):
PUBLIC = "public"            # no credentials needed
ANY = "any"                  # every authenticated role (incident:read)
SECURITY = "security"        # ssh:detail
SAFETY = "safety"            # camera:detail / person:detail
OPERATIONS = "operations"    # maintenance:detail + environment:detail
ADMIN = "admin"              # scenario:execute or administrator role only
KIND = "kind"                # the {kind} domain's detail permission
LOOKUP = "lookup"            # resource lookup filtered by permission; unknown ID is 404 for everyone
UNSUPPORTED = "unsupported"  # this {kind} is not served by the route (404/422 for everyone)
KIND_ROLE = {"ssh": SECURITY, "ppe": SAFETY, "face": SAFETY, "maintenance": OPERATIONS, "environment": OPERATIONS}
GROUP_ROLE = {SECURITY: {"security_operator"}, SAFETY: {"safety_operator"}, OPERATIONS: {"operations_engineer"}}

POLICY = {
    ("GET", "/api/v1/health"): PUBLIC,
    ("GET", "/api/v1/auth/me"): ANY,
    ("GET", "/api/v1/incidents"): ANY,
    ("GET", "/api/v1/incidents/{scenario_id}"): LOOKUP,
    ("GET", "/api/v1/incidents/{scenario_id}/evidence/{event_id}"): LOOKUP,
    ("GET", "/api/v1/incidents/{scenario_id}/graph"): LOOKUP,
    ("GET", "/api/v1/incidents/{scenario_id}/graph-integrity"): LOOKUP,
    ("GET", "/api/v1/scenarios"): ANY,
    ("POST", "/api/v1/scenarios/{name}/run"): ADMIN,
    ("POST", "/api/v1/custom-scenarios/environment"): ADMIN,
    ("GET", "/api/v1/topology/options"): ANY,
    ("GET", "/api/v1/topology/cameras"): SAFETY,
    ("GET", "/api/v1/events/standalone"): ANY,
    ("POST", "/api/v1/events/standalone"): ADMIN,
    # Employee directory and zone grants: administrators only.
    ("GET", "/api/v1/access/employees"): ADMIN,
    ("POST", "/api/v1/access/employees"): ADMIN,
    ("POST", "/api/v1/access/employees/{person_id}/zones"): ADMIN,
    # Domain feeds: each needs its domain's detail permission (operator decision
    # 2026-10-12; maintenance/environment were open to every role before).
    ("GET", "/api/v1/ssh/published"): SECURITY,
    ("GET", "/api/v1/ppe/observations"): SAFETY,
    ("GET", "/api/v1/face/observations"): SAFETY,
    ("GET", "/api/v1/maintenance/events"): OPERATIONS,
    ("GET", "/api/v1/environment/events"): OPERATIONS,
    # Filtered by the caller's detail permissions inside the handler.
    ("GET", "/api/v1/correlations/pairs"): ANY,
    ("GET", "/api/v1/decisions/standalone"): ANY,
    ("GET", "/api/v1/evidence-reviews"): ANY,
    # Uploads: each domain's operator uploads its own domain (operator decision 2026-10-12).
    ("POST", "/api/v1/ppe/validate-image"): SAFETY,
    ("POST", "/api/v1/face/validate-image"): SAFETY,
    ("POST", "/api/v1/maintenance/validate"): OPERATIONS,
    ("POST", "/api/v1/environment/validate"): OPERATIONS,
    ("POST", "/api/v1/ssh/validate-log"): SECURITY,
    ("POST", "/api/v1/ssh/process-log"): SECURITY,
    ("POST", "/api/v1/ssh/publish"): SECURITY,
    # Single records.
    ("GET", "/api/v1/ppe/observations/{observation_id}"): SAFETY,
    ("GET", "/api/v1/ppe/observations/{observation_id}/image"): SAFETY,
    ("GET", "/api/v1/face/observations/{oid}"): SAFETY,
    ("GET", "/api/v1/face/observations/{oid}/image"): SAFETY,
    ("GET", "/api/v1/face/observations/{oid}/authorization"): SAFETY,
    ("GET", "/api/v1/image-observations/{kind}/{observation_id}/metadata"): KIND,
    ("POST", "/api/v1/images/{kind}/{observation_id}/capture-declaration"): ADMIN,  # declares controlled metadata
    ("GET", "/api/v1/evidence/{kind}/{event_id}/graph"): KIND,
    ("GET", "/api/v1/evidence-reviews/{kind}/{evidence_id}"): KIND,
    ("POST", "/api/v1/evidence-reviews/{kind}/{evidence_id}"): KIND,
    # Investigation lifecycle: {subject_type} is a group or an Evidence kind (not expanded here).
    ("GET", "/api/v1/lifecycle/{subject_type}/{subject_id}"): LOOKUP,
    ("POST", "/api/v1/lifecycle/{subject_type}/{subject_id}/transitions"): LOOKUP,
    ("GET", "/api/v1/evidence/{kind}/{evidence_id}/specialist"): KIND,
    ("POST", "/api/v1/evidence/{kind}/{evidence_id}/specialist"): KIND,  # then scenario:execute after lookup
    # SSH pipeline steps.
    ("POST", "/api/v1/ssh/published/{event_id}/check-correlation"): SECURITY,
    ("PUT", "/api/v1/ssh/published/{event_id}/controlled-time"): ADMIN,  # declares controlled metadata
    ("GET", "/api/v1/ssh/published/{event_id}/decision"): SECURITY,
    ("POST", "/api/v1/ssh/published/{event_id}/decision"): SECURITY,
    ("POST", "/api/v1/ssh/published/{event_id}/ingest-graph"): SECURITY,
    ("GET", "/api/v1/ssh/published/{event_id}/reasoning-preview"): SECURITY,
    ("POST", "/api/v1/ssh/published/{event_id}/run-pipeline"): SECURITY,
    ("POST", "/api/v1/ssh/published/{event_id}/specialist-response"): SECURITY,
    ("POST", "/api/v1/decisions/ssh/{event_id}/reevaluate"): SECURITY,
    # Correlations.
    ("POST", "/api/v1/correlations/check-published"): ADMIN,  # checks every domain permission
    ("GET", "/api/v1/operations/correlations"): OPERATIONS,
    ("GET", "/api/v1/operations/correlations/{candidate_id}/decision"): OPERATIONS,
    ("POST", "/api/v1/operations/correlations/{candidate_id}/decision"): OPERATIONS,
    ("GET", "/api/v1/operations/correlations/{candidate_id}/graph"): OPERATIONS,
    ("POST", "/api/v1/decisions/operations/{candidate_id}/reevaluate"): OPERATIONS,
    ("GET", "/api/v1/physical/image-correlations"): SAFETY,
    ("GET", "/api/v1/physical/image-correlations/{candidate_id}/graph"): SAFETY,
    ("GET", "/api/v1/physical/image-correlations/{candidate_id}/person-association"): SAFETY,
    ("GET", "/api/v1/physical/image-correlations/{candidate_id}/review-decision"): SAFETY,
    ("GET", "/api/v1/physical/image-correlations/{candidate_id}/specialist"): SAFETY,
    ("POST", "/api/v1/physical/image-correlations/{candidate_id}/specialist"): SAFETY,
    # Cross-domain views need every domain's detail permission: administrators.
    ("GET", "/api/v1/cyber/face-ssh/candidates"): ADMIN,
    ("GET", "/api/v1/cyber/face-ssh/candidates/{candidate_id}/specialists"): ADMIN,
    ("POST", "/api/v1/cyber/face-ssh/candidates/{candidate_id}/specialists"): ADMIN,
    ("GET", "/api/v1/correlations/unified"): ADMIN,
    ("GET", "/api/v1/correlations/unified/{group_id}/graph"): ADMIN,
    ("GET", "/api/v1/correlations/unified/{group_id}/review-decision"): ADMIN,
    ("GET", "/api/v1/correlations/unified/{group_id}/specialists"): ADMIN,
    ("POST", "/api/v1/correlations/unified/{group_id}/specialists"): ADMIN,
    ("GET", "/api/v1/correlations/unified/{group_id}/synthesis"): ADMIN,
    ("GET", "/api/v1/reviews/unified/{group_id}/records"): ADMIN,
    ("POST", "/api/v1/reviews/unified/{group_id}/records"): ADMIN,
    ("GET", "/api/v1/reviews/audit-integrity"): ADMIN,
    # AI Investigator.
    ("GET", "/api/v1/investigator/evidence/{kind}/{evidence_id}/context"): KIND,
    ("POST", "/api/v1/investigator/evidence/{kind}/{evidence_id}/ask"): KIND,
    ("GET", "/api/v1/investigator/evidence/{kind}/{evidence_id}/history"): KIND,
    ("POST", "/api/v1/investigator/evidence/{kind}/{evidence_id}/history"): KIND,
    ("DELETE", "/api/v1/investigator/evidence/{kind}/{evidence_id}/history"): KIND,
    ("GET", "/api/v1/investigator/operations/{candidate_id}/context"): OPERATIONS,
    ("POST", "/api/v1/investigator/operations/{candidate_id}/ask"): OPERATIONS,
    ("GET", "/api/v1/investigator/operations/{candidate_id}/graph"): OPERATIONS,
    ("GET", "/api/v1/investigator/operations/{candidate_id}/history"): OPERATIONS,
    ("POST", "/api/v1/investigator/operations/{candidate_id}/history"): OPERATIONS,
    ("DELETE", "/api/v1/investigator/operations/{candidate_id}/history"): OPERATIONS,
    ("GET", "/api/v1/investigator/pairs/{pair_id}/context"): LOOKUP,
    ("POST", "/api/v1/investigator/pairs/{pair_id}/ask"): LOOKUP,
    ("GET", "/api/v1/investigator/pairs/{pair_id}/history"): LOOKUP,
    ("POST", "/api/v1/investigator/pairs/{pair_id}/history"): LOOKUP,
    ("DELETE", "/api/v1/investigator/pairs/{pair_id}/history"): LOOKUP,
    ("GET", "/api/v1/investigator/unified/{group_id}/context"): ADMIN,
    ("POST", "/api/v1/investigator/unified/{group_id}/ask"): ADMIN,
    ("GET", "/api/v1/investigator/unified/{group_id}/graph"): ADMIN,
    ("GET", "/api/v1/investigator/unified/{group_id}/history"): ADMIN,
    ("POST", "/api/v1/investigator/unified/{group_id}/history"): ADMIN,
    ("DELETE", "/api/v1/investigator/unified/{group_id}/history"): ADMIN,
}
# {kind} values a route does not serve: answered 404/422 before any permission matters.
UNSUPPORTED_KINDS = {
    ("GET", "/api/v1/image-observations/{kind}/{observation_id}/metadata"): {"ssh", "maintenance", "environment"},
    ("POST", "/api/v1/images/{kind}/{observation_id}/capture-declaration"): {"ssh", "maintenance", "environment"},
    ("GET", "/api/v1/evidence/{kind}/{event_id}/graph"): {"ppe", "face"},
}
# Valid bodies where the schema alone cannot produce one (field patterns).
BODIES = {
    ("POST", "/api/v1/access/employees"): {"person_id": "P999", "role": "ENGINEER"},
    ("POST", "/api/v1/access/employees/{person_id}/zones"): {"zone_id": "ZONE-A", "action": "GRANT"},
    ("POST", "/api/v1/correlations/check-published"): {"kind": "ppe", "observation_ids": ["X"]},
    ("POST", "/api/v1/custom-scenarios/environment"): {"zone_id": "ZONE-A",
                                                        "environmental": {"sensor_id": "SEN-A-01", "temperature_c": 30}},
    ("POST", "/api/v1/ssh/publish"): {"preview_id": "SSH-PREVIEW-" + "A" * 32, "indices": [0]},
}
PATH_VALUES = {"person_id": "P999"}
# Real zone/server for body fields, so zone checks pass and the permission check is what is tested.
FIELD_VALUES = {"zone_id": "ZONE-A", "server_id": "SRV-A1-01"}

SPEC = app.openapi()


def resolve(schema):
    while "$ref" in schema:
        schema = SPEC["components"]["schemas"][schema["$ref"].split("/")[-1]]
    if "anyOf" in schema:
        return resolve(next((x for x in schema["anyOf"] if x.get("type") != "null"), schema["anyOf"][0]))
    return schema


def example(schema):
    schema = resolve(schema)
    if "enum" in schema:
        return schema["enum"][0]
    if "const" in schema:
        return schema["const"]
    kind = schema.get("type")
    if kind == "object":
        return {k: FIELD_VALUES.get(k, example(v)) for k, v in schema.get("properties", {}).items() if k in schema.get("required", [])}
    return {"array": [], "integer": 1, "number": 0.5, "boolean": True}.get(kind, "X" * max(schema.get("minLength", 1), 20))


def request_for(method, template):
    if (method, template) in BODIES:
        return {"json": BODIES[(method, template)]}
    content = SPEC["paths"][template][method.lower()].get("requestBody", {}).get("content", {})
    if "application/json" in content:
        return {"json": example(content["application/json"]["schema"])}
    if "multipart/form-data" in content:
        schema = resolve(content["multipart/form-data"]["schema"])
        files, data = {}, {}
        for name, field in schema.get("properties", {}).items():
            field = resolve(field)
            if field.get("format") == "binary" or field.get("contentMediaType"):
                files[name] = ("probe.bin", b"probe", "application/octet-stream")
            elif name in schema.get("required", []):
                data[name] = str(FIELD_VALUES.get(name, example(field)))
        return {"files": files or None, "data": data}
    return {}


def operations():
    for template, item in sorted(SPEC["paths"].items()):
        for method in item:
            kinds = KINDS if "{kind}" in template else (None,)
            for kind in kinds:
                path = template.replace("{kind}", kind) if kind else template
                url = re.sub(r"\{([^}]+)\}", lambda m: PATH_VALUES.get(m.group(1), "X"), path)
                yield method.upper(), template, kind, url


OPS = list(operations())


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv("NEO4J_URI", "bolt://127.0.0.1:1")
    monkeypatch.setenv("DCG_INVESTIGATOR_ENABLED", "0")
    # Same outcome locally and in CI, whatever the operator's .env says.
    monkeypatch.setenv("DCG_INVESTIGATOR_HISTORY_ENABLED", "0")
    from openai import OpenAI
    def forbidden(*args, **kwargs):
        raise AssertionError("Unexpected OpenAI call")
    monkeypatch.setattr(OpenAI, "__init__", forbidden)
    yield
    app.dependency_overrides.pop(current_principal, None)


def test_every_operation_is_classified():
    documented = {(m.upper(), p) for p, item in SPEC["paths"].items() for m in item}
    assert documented - set(POLICY) == set(), "Classify new endpoints in POLICY"
    assert set(POLICY) - documented == set(), "Remove endpoints that no longer exist"


def test_no_operation_answers_without_credentials():
    client = TestClient(app, raise_server_exceptions=False)
    for method, template, _, url in OPS:
        status = client.request(method, url, **request_for(method, template)).status_code
        expected = 200 if POLICY[(method, template)] == PUBLIC else 401
        assert status == expected, (method, url, status)


@pytest.mark.parametrize("role", ROLES)
def test_roles_are_refused_exactly_where_they_lack_permission(role):
    app.dependency_overrides[current_principal] = lambda: Principal("matrix", frozenset({role}), ALL_ZONES)
    client = TestClient(app, raise_server_exceptions=False)
    problems = []
    for method, template, kind, url in OPS:
        rule = POLICY[(method, template)]
        if kind in UNSUPPORTED_KINDS.get((method, template), ()):
            rule = UNSUPPORTED
        elif rule == KIND:
            rule = KIND_ROLE[kind]
        status = client.request(method, url, **request_for(method, template)).status_code
        if status in (401, 500):
            problems.append((method, url, status, "unexpected"))
        elif rule in (PUBLIC, ANY):
            ok = status != 403
        elif rule in (LOOKUP, UNSUPPORTED):
            ok = status in (403, 404, 422)
        else:
            permitted = role in GROUP_ROLE.get(rule, set())
            ok = (status != 403) if permitted else (status == 403)
        if status not in (401, 500) and not ok:
            problems.append((method, url, status, rule))
    assert problems == []
