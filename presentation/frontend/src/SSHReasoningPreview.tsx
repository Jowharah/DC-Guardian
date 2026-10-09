import {useState} from "react";
import {previewSSHReasoning,type SSHReasoningPreview as Preview} from "./api";
export default function SSHReasoningPreview({eventId}:{eventId:string}){
 const [result,setResult]=useState<Preview|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 async function check(){setBusy(true);setError("");try{setResult(await previewSSHReasoning(eventId))}catch(e){setError(e instanceof Error?e.message:"Reasoning adapter validation unavailable")}finally{setBusy(false)}}
 return <div className="evidenceItem"><button disabled={busy} onClick={()=>void check()}>{busy?"Checking…":"Validate Reasoning contract"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<p className="muted">{result.status} · Original time: {result.original_timestamp??"Unknown"} · Source IP: {result.source_ip??"Unknown"}. Adapter only; topology mapping, correlation, Response and Decision have not run.</p>}</div>
}
