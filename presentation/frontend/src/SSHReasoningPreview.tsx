import {useState} from "react";
import {runSSHPipeline,ingestSSHGraph,checkSSHCorrelation,getSSHSpecialistResponse,evaluateSSHDecision,type SSHDecisionResult,type SSHSpecialistResponse,type SSHCorrelationCheck,type SSHGraphIngestion,type SSHPipelineRun} from "./api";
export default function SSHReasoningPreview({eventId}:{eventId:string}){
 const [result,setResult]=useState<SSHPipelineRun|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const [ingested,setIngested]=useState<SSHGraphIngestion|null>(null);
 const [correlation,setCorrelation]=useState<SSHCorrelationCheck|null>(null);
 const [specialist,setSpecialist]=useState<SSHSpecialistResponse|null>(null);
 const [decision,setDecision]=useState<SSHDecisionResult|null>(null);
 async function run(){setBusy(true);setError("");try{setResult(await runSSHPipeline(eventId))}catch(e){setError(e instanceof Error?e.message:"Pipeline execution unavailable")}finally{setBusy(false)}}
 async function ingest(){setBusy(true);setError("");try{setIngested(await ingestSSHGraph(eventId))}catch(e){setError(e instanceof Error?e.message:"Graph ingestion unavailable")}finally{setBusy(false)}}
 async function correlate(){setBusy(true);setError("");try{setCorrelation(await checkSSHCorrelation(eventId))}catch(e){setError(e instanceof Error?e.message:"Correlation unavailable")}finally{setBusy(false)}}
 async function respond(){setBusy(true);setError("");try{setSpecialist(await getSSHSpecialistResponse(eventId))}catch(e){setError(e instanceof Error?e.message:"Specialist unavailable")}finally{setBusy(false)}}
 async function evaluate(){setBusy(true);setError("");try{const outcome=await evaluateSSHDecision(eventId);setDecision(outcome);setSpecialist(outcome.specialist);setCorrelation(outcome.correlation)}catch(e){setError(e instanceof Error?e.message:"Decision unavailable")}finally{setBusy(false)}}
 return <div className="evidenceItem"><button disabled={busy} onClick={()=>void run()}>{busy?"Running checks…":"Run Through Pipeline"}</button>
 <button disabled={busy} onClick={()=>void ingest()}>Ingest SSH Evidence into Neo4j</button>
 <button disabled={busy} onClick={()=>void correlate()}>Check Correlation</button>
 <button disabled={busy} onClick={()=>void respond()}>Run Cybersecurity Specialist</button>
 <button disabled={busy} onClick={()=>void evaluate()}>{busy?"Processing…":"Evaluate Standalone SSH Decision"}</button>
 {decision&&<section className="evidenceItem"><h4>Decision · <span className={`severity severity-${decision.decision.severity.toLowerCase()}`}>{decision.decision.severity}</span></h4><p>Status: {decision.decision.incident_status} · Response: {decision.decision.response_mode}</p><p>Rules: {decision.decision.decision_rules_triggered.join(", ")}</p><p className="muted">Policy: {decision.decision.policy_version} · Autonomous action disabled · Standalone SSH evidence, not a correlated incident.</p></section>}
 {specialist&&<section className="evidenceItem"><h4>Cybersecurity Specialist · {specialist.grounding_status}</h4><p>{specialist.assessment}</p><h5>Supported findings</h5><ul>{specialist.supported_findings.map((v,i)=><li key={i}>{v}</li>)}</ul><h5>Recommended considerations</h5><ul>{specialist.recommended_considerations.map((v,i)=><li key={i}>{v}</li>)}</ul><h5>Limitations</h5><ul>{specialist.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul><h5>Approved citations</h5><ul>{specialist.citations.map((v,i)=><li key={i}>{v.document_id} · {v.chunk_id}</li>)}</ul><p className="muted">Specialist analysis only. No Decision severity assigned.</p></section>}
 {correlation&&<p role="status">Correlation: {correlation.status.replaceAll("_"," ")} · Matches: {correlation.correlation_count} · {correlation.note}</p>}
 {ingested&&<p role="status">INGESTED · Graph event: {ingested.graph_event_id} · Source IP: {ingested.source_ip}. Correlation, Response and Decision not yet run.</p>}
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div><h4>Pipeline execution status</h4>{result.stages.map(stage=><div className="sshPipelineStage" key={stage.stage}><b>{stage.stage.replaceAll("_"," ")}</b><span className={stage.status==="COMPLETE"?"sshStageComplete":"sshStagePending"}>{stage.status}</span><small>{stage.detail}</small></div>)}<p className="muted">{result.note}</p><p className="muted">Full pipeline: NOT COMPLETE · no Decision severity assigned.</p></div>}</div>
}
