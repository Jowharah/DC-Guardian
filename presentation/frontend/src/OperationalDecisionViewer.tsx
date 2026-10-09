import {useEffect,useState} from "react";
import {getOperationalDecision,evaluateOperationalDecision,type OperationalDecisionResult} from "./api";
export default function OperationalDecisionViewer({candidateId}:{candidateId:string}){
 const [saved,setSaved]=useState<OperationalDecisionResult|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{let active=true;setSaved(null);setError("");
   getOperationalDecision(candidateId).then(v=>{if(active)setSaved(v)})
     .catch(e=>{if(active&&!(e instanceof Error&&e.message.includes("(404)")))setError("Saved Decision lookup unavailable")});
   return()=>{active=false}},[candidateId]);
 async function run(){setBusy(true);setError("");
  try{setSaved(await evaluateOperationalDecision(candidateId))}
  catch(e){setError(e instanceof Error?e.message:"Correlated Decision unavailable")}
  finally{setBusy(false)}}
 return <section className="specialistAnalysis"><h4>Correlated Operations Specialist and Decision</h4>
 <p className="muted">Grounded cross-domain assessment and deterministic Decision v1. Requires verified Neo4j Evidence and approved knowledge. Human review only.</p>
 <button disabled={busy} onClick={()=>void run()}>{busy?"Evaluating…":saved?"Re-evaluate Correlated Decision":"Evaluate Correlated Decision"}</button>
 {error&&<p className="error" role="alert">{error}</p>}
 {saved&&<><div className="evidenceItem"><div className="incidentTop"><b>Decision · <span className={`severity severity-${saved.decision.severity.toLowerCase()}`}>{saved.decision.severity}</span></b><span>{saved.decision.incident_status}</span></div>
 <p>{saved.decision.response_mode} · {saved.decision.policy_version} · Autonomous action disabled</p><p>Evaluated: {new Date(saved.evaluated_at).toLocaleString()}</p>
 <b>Triggered Decision rules</b><ul>{saved.decision.decision_rules_triggered.map(x=><li key={x}>{x}</li>)}</ul></div>
 <article className="evidenceItem"><div className="incidentTop"><b>OPERATIONS SPECIALIST</b><span className="mode">{saved.specialist.grounding_status}</span></div>
 <p>{saved.specialist.assessment}</p><b>Supported findings</b><ul>{saved.specialist.supported_findings.map((x,i)=><li key={i}>{x}</li>)}</ul>
 <b>Recommended considerations</b><ul>{saved.specialist.recommended_considerations.map((x,i)=><li key={i}>{x}</li>)}</ul>
 <b>Limitations</b><ul>{saved.specialist.limitations.map((x,i)=><li key={i}>{x}</li>)}</ul>
 <b>Approved knowledge citations</b><ul>{saved.specialist.citations.map((x,i)=><li key={i}>{x.document_id} / {x.chunk_id}</li>)}</ul></article></>}
 </section>;
}
