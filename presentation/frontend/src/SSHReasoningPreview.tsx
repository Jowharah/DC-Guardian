import {useState} from "react";
import {runSSHPipeline,ingestSSHGraph,checkSSHCorrelation,type SSHCorrelationCheck,type SSHGraphIngestion,type SSHPipelineRun} from "./api";
export default function SSHReasoningPreview({eventId}:{eventId:string}){
 const [result,setResult]=useState<SSHPipelineRun|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 const [ingested,setIngested]=useState<SSHGraphIngestion|null>(null);
 const [correlation,setCorrelation]=useState<SSHCorrelationCheck|null>(null);
 async function run(){setBusy(true);setError("");try{setResult(await runSSHPipeline(eventId))}catch(e){setError(e instanceof Error?e.message:"Pipeline execution unavailable")}finally{setBusy(false)}}
 async function ingest(){setBusy(true);setError("");try{setIngested(await ingestSSHGraph(eventId))}catch(e){setError(e instanceof Error?e.message:"Graph ingestion unavailable")}finally{setBusy(false)}}
 async function correlate(){setBusy(true);setError("");try{setCorrelation(await checkSSHCorrelation(eventId))}catch(e){setError(e instanceof Error?e.message:"Correlation unavailable")}finally{setBusy(false)}}
 return <div className="evidenceItem"><button disabled={busy} onClick={()=>void run()}>{busy?"Running checks…":"Run Through Pipeline"}</button>
 <button disabled={busy} onClick={()=>void ingest()}>Ingest SSH Evidence into Neo4j</button>
 <button disabled={busy} onClick={()=>void correlate()}>Check Correlation</button>
 {correlation&&<p role="status">Correlation: {correlation.status.replaceAll("_"," ")} · Matches: {correlation.correlation_count} · {correlation.note}</p>}
 {ingested&&<p role="status">INGESTED · Graph event: {ingested.graph_event_id} · Source IP: {ingested.source_ip}. Correlation, Response and Decision not yet run.</p>}
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div><h4>Pipeline execution status</h4>{result.stages.map(stage=><div className="sshPipelineStage" key={stage.stage}><b>{stage.stage.replaceAll("_"," ")}</b><span className={stage.status==="COMPLETE"?"sshStageComplete":"sshStagePending"}>{stage.status}</span><small>{stage.detail}</small></div>)}<p className="muted">{result.note}</p><p className="muted">Full pipeline: NOT COMPLETE · no Decision severity assigned.</p></div>}</div>
}
