import type {PublishedSSH} from "./api";
export default function SSHEvidenceDetails({event}:{event:PublishedSSH}){
 return <section className="evidenceItem">
 <h4>SSH Detector Evidence</h4>
 <p><b>{event.evidence_state}</b> · {event.zone_id} · {event.server_id}</p>
 <div className="standaloneMeta">
 <div><small>Source IP</small><strong>{event.source_ip??"Unknown"}</strong></div>
 <div><small>Original log window</small><strong>{event.window_start??"Unknown"}</strong><small>Historical log timestamp; timezone may be unspecified</small></div>
 <div><small>Received</small><strong>{new Date(event.received_at).toLocaleString()}</strong></div>
 </div>
 <p>Usernames: {event.usernames.join(", ")||"Unavailable"} · Detector votes: {event.detector_votes}</p>
 <h4>Frozen detector metrics</h4>
 <pre className="ppeJson">{JSON.stringify(event.evidence,null,2)}</pre>
 {event.decision_record&&<div className="evidenceItem">
 <h4>Saved standalone SSH Decision · {event.decision_record.decision.severity}</h4>
 <p>{event.decision_record.decision.incident_status} · {event.decision_record.decision.response_mode} · {event.decision_record.decision.policy_version}</p>
 <p>Evaluated: {new Date(event.decision_record.evaluated_at).toLocaleString()}</p>
 <details><summary>Saved Cybersecurity Specialist · {event.decision_record.specialist.grounding_status}</summary>
 <p>{event.decision_record.specialist.assessment}</p>
 <ul>{event.decision_record.specialist.supported_findings.map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Limitations</h4><ul>{event.decision_record.specialist.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul>
 </details>
 <p className="muted">This Decision applies only to standalone SSH Evidence. No severity is inherited by the cross-domain candidate.</p>
 </div>}
 <p className="muted">Original raw SSH log not retained. No verified identity-to-SSH attribution.</p>
 </section>;
}
