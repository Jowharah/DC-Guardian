import {useState} from "react";
import {runSSHPipeline,type SSHPipelineRun} from "./api";
export default function SSHReasoningPreview({eventId}:{eventId:string}){
 const [result,setResult]=useState<SSHPipelineRun|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function run(){setBusy(true);setError("");try{setResult(await runSSHPipeline(eventId))}catch(e){setError(e instanceof Error?e.message:"Pipeline execution unavailable")}finally{setBusy(false)}}
 return <div className="evidenceItem"><button disabled={busy} onClick={()=>void run()}>{busy?"Running checks…":"Run Through Pipeline"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div><h4>Pipeline execution status</h4>{result.stages.map(stage=><div className="sshPipelineStage" key={stage.stage}><b>{stage.stage.replaceAll("_"," ")}</b><span className={stage.status==="COMPLETE"?"sshStageComplete":"sshStagePending"}>{stage.status}</span><small>{stage.detail}</small></div>)}<p className="muted">{result.note}</p><p className="muted">Full pipeline: NOT COMPLETE · no Decision severity assigned.</p></div>}</div>
}
