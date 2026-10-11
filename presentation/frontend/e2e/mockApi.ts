/**
 * Stateful mock of the DC-GUARDIAN API for browser tests.
 *
 * Synthetic data only (no operator data). Shapes follow the real FastAPI
 * responses. Verdicts, group reviews, specialist evaluation and Decision
 * re-evaluation change state exactly as the backend contracts describe, so
 * the tests exercise real UI flows without a backend, Neo4j or OpenAI.
 */
import type {Page, Route} from "@playwright/test";

const NOW = "2026-10-11T08:00:00+00:00";
export const PPE_ID = "PPE-IMG-TEST0001";
export const FACE_ID = "FACE-IMG-TEST0001";
export const SSH_ID = "SSH-EVT-TEST0001";
export const GROUP_ID = "DCG-UNIFIED-TEST00000000000001";

type Verdict = {audit_id: string; kind: string; evidence_id: string; zone_id: string; reviewer: string;
  recorded_at: string; verdict: string; corrected_status: string | null; model_status: string | null; rationale: string;
  previous_hash: string; entry_hash: string};

export type MockState = {
  verdicts: Verdict[];
  groupReviews: Record<string, unknown>[];
  specialistsEvaluated: boolean;
  sshInputOverridden: boolean;
  sshReevaluated: boolean;
  requests: {method: string; path: string; body: unknown}[];
};

const MODEL_STATUS: Record<string, string> = {ppe: "NON_COMPLIANT", face: "RECOGNIZED", ssh: "HIGH_CONFIDENCE_ANOMALY"};
const VOCABULARY: Record<string, string[]> = {
  ppe: ["COMPLIANT", "NON_COMPLIANT"], face: ["AUTHORIZED", "NO_FACE", "UNAUTHORIZED", "UNKNOWN_PERSON"],
  ssh: ["BENIGN", "ANOMALOUS"], maintenance: ["HEALTHY", "AT_RISK"], environment: ["NORMAL", "ABNORMAL"],
};
// 1x1 transparent PNG.
const PNG = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");

const ppeObservation = {observation_id: PPE_ID, zone_id: "ZONE-B", created_at: NOW, status: "NON_COMPLIANT",
  person_count: 1, source_type: "OPERATOR_UPLOADED_IMAGE", pipeline_status: "PPE_ONLY_NOT_INTEGRATED", review_status: "NOT_REVIEWED"};
const ppeDetail = {observation_id: PPE_ID, zone_id: "ZONE-B", created_at: NOW, image_size: {width: 100, height: 100},
  assessment: {overall_status: "NON_COMPLIANT", person_count: 1, required_ppe: ["helmet", "safety-vest"],
    people: [{person_index: 0, status: "NON_COMPLIANT", required_ppe: ["helmet", "safety-vest"], required_ppe_detected: ["helmet"],
      required_ppe_not_detected: ["safety-vest"], optional_ppe_detected: [], all_associated_classes: ["helmet"]}],
    detections: [], unassigned_detections: []},
  pipeline_status: "PPE_ONLY_NOT_INTEGRATED", review_status: "NOT_REVIEWED"};
const faceObservation = {observation_id: FACE_ID, zone_id: "ZONE-B", created_at: NOW, recognition_status: "RECOGNIZED",
  person_id: "P009", review_status: "NOT_REVIEWED", pipeline_status: "FACE_ONLY_NOT_INTEGRATED"};

function decision(severity: string | null, status = "REVIEW_REQUIRED") {
  return {incident_status: status, severity, response_mode: severity ? "HUMAN_REVIEW" : "NO_ACTION_ASSIGNED",
    escalation_required: false, autonomous_action_allowed: false,
    decision_rules_triggered: severity ? ["CYBERSECURITY_ANOMALY_EVIDENCE"] : [], rationale: [], policy_version: "DCG-DECISION-v1"};
}

function sshRecord(state: MockState) {
  const original = decision("MEDIUM");
  const current = state.sshReevaluated ? decision(null, "INPUT_CLEARED_BY_HUMAN_VERDICT") : original;
  return {evaluated_at: NOW, decision: current, original_decision: original,
    specialist: {specialist_id: "cybersecurity", grounding_status: "SUPPORTED", assessment: "Synthetic.",
      supported_findings: [], recommended_considerations: [], limitations: [], citations: []},
    correlation: {status: "NO_CORRELATION"},
    reevaluation: state.sshReevaluated ? {reevaluation_id: "DCG-RE-TEST", evaluated_at: NOW, evaluated_by: "test-operator", inputs: {}} : null,
    input_review: {reevaluation_required: state.sshInputOverridden && !state.sshReevaluated,
      changed_inputs: state.sshInputOverridden && !state.sshReevaluated ? [`ssh:${SSH_ID}`] : [],
      current_inputs: {[`ssh:${SSH_ID}`]: {abnormal: !state.sshInputOverridden, status: state.sshInputOverridden ? "BENIGN" : null,
        source: state.sshInputOverridden ? "HUMAN_OVERRIDE" : "DETECTOR", verdict_audit_id: null}}}};
}

function sshPublished(state: MockState) {
  return {event_id: SSH_ID, received_at: NOW, zone_id: "ZONE-B", server_id: "SRV-B1-01", source_ip: "203.0.113.50",
    window_start: "2026-10-11T07:55:00+00:00", window_end: "2026-10-11T08:00:00+00:00", evidence_state: "HIGH_CONFIDENCE_ANOMALY",
    detector_votes: 2, detector_combination: "RULE+AE", explicit_security_signal: false, usernames: ["root"],
    evidence: {failed_login_count: 6, successful_login_count: 0}, anomaly_detected: true, confidence: "MEDIUM", security_signals: [],
    record_type: "SSH_DETECTOR_EVIDENCE", source_type: "OPERATOR_UPLOADED_OPENSSH_LOG", decision_severity: null,
    decision_record: sshRecord(state)};
}

const group = {id: GROUP_ID, zone_id: "ZONE-B", domains: ["CYBERSECURITY", "PHYSICAL_SECURITY", "SAFETY"],
  evidence: [{kind: "face", domain: "PHYSICAL_SECURITY", observation_id: FACE_ID}, {kind: "ppe", domain: "SAFETY", observation_id: PPE_ID},
    {kind: "ssh", domain: "CYBERSECURITY", observation_id: SSH_ID}],
  edges: [{type: "PHYSICAL_IMAGE", left: ["ppe", PPE_ID], right: ["face", FACE_ID], source_id: "PAIR-1", zone_id: "ZONE-B", details: {}},
    {type: "FACE_SSH_CONTEXT", left: ["face", FACE_ID], right: ["ssh", SSH_ID], source_id: "PAIR-2", zone_id: "ZONE-B", details: {}}],
  source_candidate_ids: ["PAIR-1", "PAIR-2"], status: "CORRELATION_GROUP_CANDIDATE", decision: {incident_status: "REVIEW_REQUIRED", severity: "HIGH", response_mode: "HUMAN_REVIEW", escalation_required: true,
    autonomous_action_allowed: false, decision_rules_triggered: ["LINKED_GROUP_ESCALATION"], rationale: [], policy_version: "DCG-DECISION-v2",
    validation_status: "VALIDATED_ON_AUTHOR_LABELS_INDEPENDENT_LABELS_PENDING"}, decision_severity: "HIGH",
  severity_policy: "DCG-DECISION-v2", severity_rules_triggered: ["CYBERSECURITY_ANOMALY_EVIDENCE", "LINKED_GROUP_ESCALATION"],
  base_severity: "MEDIUM", escalated: true, linkage_rule: "L2_KNOWN_MECHANISM_WITHIN_10_MIN",
  linkage: {same_server: false, same_rack: false, unauthorized_with_cyber: false, known_mechanism: true, time_spread_minutes: 4},
  active_concern_domains: ["CYBERSECURITY", "PHYSICAL_SECURITY", "SAFETY"], severity_provisional: true, members: [],
  autonomous_action_allowed: false, identity_link_established: false, causal_relationship_established: false, note: "Synthetic group."};

function latestVerdicts(state: MockState) {
  const latest = new Map<string, Verdict>();
  for (const v of state.verdicts) latest.set(`${v.kind}:${v.evidence_id}`, v);
  return [...latest.values()].map(v => ({kind: v.kind, evidence_id: v.evidence_id, zone_id: v.zone_id, verdict: v.verdict,
    corrected_status: v.corrected_status, model_status: v.model_status, recorded_at: v.recorded_at, reviewer: v.reviewer,
    effective_status: v.verdict === "OVERRIDDEN" ? v.corrected_status : v.model_status}));
}

function effective(records: Verdict[]) {
  const last = records.at(-1);
  if (!last) return null;
  const overridden = last.verdict === "OVERRIDDEN";
  return {verdict: last.verdict, model_status: last.model_status, effective_status: overridden ? last.corrected_status : last.model_status,
    abnormal: overridden ? !["COMPLIANT", "AUTHORIZED", "NO_FACE", "BENIGN", "HEALTHY", "NORMAL"].includes(last.corrected_status ?? "") : null,
    recorded_at: last.recorded_at, reviewer: last.reviewer, source: overridden ? "HUMAN_OVERRIDE" : `HUMAN_${last.verdict}`};
}

export async function installMockApi(page: Page): Promise<MockState> {
  const state: MockState = {verdicts: [], groupReviews: [], specialistsEvaluated: false,
    sshInputOverridden: false, sshReevaluated: false, requests: []};
  const json = (route: Route, body: unknown, status = 200) =>
    route.fulfill({status, contentType: "application/json", body: JSON.stringify(body)});

  await page.route("**/api/**", async route => {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    const method = request.method();
    const body = request.postData() ? JSON.parse(request.postData()!) : null;
    state.requests.push({method, path, body});
    let m: RegExpMatchArray | null;

    if (path === "/api/v1/auth/me") return json(route, {username: "test-operator", roles: ["administrator"], zones: ["ZONE-A", "ZONE-B", "ZONE-C"]});
    if (path === "/api/v1/ppe/observations") return json(route, [ppeObservation]);
    if (path === `/api/v1/ppe/observations/${PPE_ID}`) return json(route, ppeDetail);
    if (path === `/api/v1/ppe/observations/${PPE_ID}/image`) return route.fulfill({status: 200, contentType: "image/png", body: PNG});
    if (path === "/api/v1/face/observations") return json(route, [faceObservation]);
    if (path === "/api/v1/ssh/published") return json(route, [sshPublished(state)]);
    if (path === `/api/v1/ssh/published/${SSH_ID}/decision` && method === "GET") return json(route, sshRecord(state));
    if (path === "/api/v1/correlations/unified") return json(route, [group]);
    if (path === "/api/v1/evidence-reviews") return json(route, latestVerdicts(state));

    if ((m = path.match(/^\/api\/v1\/evidence-reviews\/(\w+)\/([^/]+)$/))) {
      const [, kind, id] = m;
      if (method === "POST") {
        const v: Verdict = {audit_id: `DCG-ER-TEST${state.verdicts.length + 1}`, kind, evidence_id: id, zone_id: "ZONE-B",
          reviewer: "test-operator", recorded_at: NOW, verdict: body.verdict, corrected_status: body.corrected_status ?? null,
          model_status: MODEL_STATUS[kind] ?? null, rationale: body.rationale, previous_hash: "GENESIS", entry_hash: "x"};
        state.verdicts.push(v);
        if (kind === "ssh") state.sshInputOverridden = body.verdict === "OVERRIDDEN";
        return json(route, {...v, detector_output_modified: false}, 201);
      }
      const records = state.verdicts.filter(v => v.kind === kind && v.evidence_id === id);
      return json(route, {kind, evidence_id: id, records, detector_status: MODEL_STATUS[kind] ?? null,
        effective: effective(records), vocabulary: VOCABULARY[kind]});
    }

    if (path === `/api/v1/correlations/unified/${GROUP_ID}/review-decision`) {
      if (!state.specialistsEvaluated) return json(route, {detail: "Evaluate unified specialists first"}, 409);
      return json(route, {group_id: GROUP_ID, specialists_evaluated_at: NOW, member_verdicts_changed_since_review: false,
        decision: {policy_version: "DCG-UNIFIED-EVIDENCE-REVIEW-v1", status: "EVIDENCE_REVIEW_REQUIRED", response_mode: "HUMAN_REVIEW",
          review_reasons: ["CYBERSECURITY_EVIDENCE_PRESENT"], severity: "HIGH", severity_policy: "DCG-DECISION-v2",
          autonomous_action_allowed: false, note: "Synthetic."}});
    }
    if (path === `/api/v1/correlations/unified/${GROUP_ID}/specialists`) {
      if (method === "POST") state.specialistsEvaluated = true;
      if (!state.specialistsEvaluated) return json(route, {detail: "No saved unified specialist assessment"}, 404);
      return json(route, {group_id: GROUP_ID, evaluated_at: NOW, decision: null, decision_severity: null,
        specialists: {cybersecurity: {assessment: "Synthetic assessment.", supported_findings: [], recommended_considerations: [],
          grounding_status: "SUPPORTED", citations: [], limitations: []}}});
    }
    if (path === `/api/v1/reviews/unified/${GROUP_ID}/records`) {
      if (method === "POST") {
        const record = {audit_id: `DCG-HR-TEST${state.groupReviews.length + 1}`, group_id: GROUP_ID, zone_id: "ZONE-B",
          reviewer: "test-operator", recorded_at: NOW, outcome: body.outcome, rationale: body.rationale,
          evidence_signature: "sig", policy_version: "DCG-UNIFIED-EVIDENCE-REVIEW-v1", review_status: "EVIDENCE_REVIEW_REQUIRED",
          previous_hash: "GENESIS", entry_hash: "x"};
        state.groupReviews.push(record);
        return json(route, record, 201);
      }
      return json(route, {group_id: GROUP_ID, zone_id: "ZONE-B", records: state.groupReviews, note: "Synthetic."});
    }
    if (path === `/api/v1/decisions/ssh/${SSH_ID}/reevaluate` && method === "POST") {
      state.sshReevaluated = true;
      return json(route, {reevaluation_id: "DCG-RE-TEST", decision: decision(null, "INPUT_CLEARED_BY_HUMAN_VERDICT")}, 201);
    }
    if (path.endsWith("/graph")) return json(route, {scenario_id: "test", source: "NEO4J_READ_ONLY", nodes: [], edges: []});
    if (path === "/api/v1/decisions/standalone") {
      return json(route, [{kind: "ppe", evidence_id: PPE_ID, zone_id: "ZONE-B", decision: {incident_status: "REVIEW_REQUIRED", severity: "LOW",
        response_mode: "HUMAN_REVIEW", escalation_required: false, autonomous_action_allowed: false,
        decision_rules_triggered: ["PPE_NON_COMPLIANCE"], rationale: [], policy_version: "DCG-DECISION-v2",
        validation_status: "POLICY_NOT_DATA_VALIDATED", input_source: "DETECTOR", effective_state: "NON_COMPLIANT"}}]);
    }
    // Every other list endpoint is empty; anything else does not exist.
    if (method === "GET" && /^\/api\/v1\/(incidents|events\/standalone|maintenance\/events|environment\/events|operations\/correlations|physical\/image-correlations|cyber\/face-ssh\/candidates|correlations\/pairs|scenarios|topology\/options|topology\/cameras|access\/employees)$/.test(path)) {
      return json(route, []);
    }
    return json(route, {detail: "Not Found"}, 404);
  });
  return state;
}

export async function signIn(page: Page) {
  await page.goto("/");
  await page.locator("input:not([type=password])").first().fill("test-operator");
  await page.locator("input[type=password]").fill("test-password");
  await page.getByRole("button", {name: "Sign in"}).click();
  await page.getByText("Signed in: test-operator").waitFor();
}
