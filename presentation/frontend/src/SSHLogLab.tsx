import {useEffect,useState} from "react";
import PostPublicationCheck from "./PostPublicationCheck";
import {getTopologyOptions,processSSHLog,type SSHProcessResult} from "./api";
export default function SSHLogLab(){
 const [zones,setZones]=useState<{zone_id:string;servers:string[]}[]>([]);
 const [zone,setZone]=useState("ZONE-B"),[server,setServer]=useState("");
 const [file,setFile]=useState<File|null>(null),[publish,setPublish]=useState(true);
 const [result,setResult]=useState<SSHProcessResult|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{getTopologyOptions().then(setZones).catch(()=>setError("Topology unavailable"))},[]);
 const servers=zones.find(x=>x.zone_id===zone)?.servers??[];
 useEffect(()=>{setServer(v=>servers.includes(v)?v:servers[0]??"")},[zone,zones]);
 async function submit(e:React.FormEvent){e.preventDefault();if(!file||!server)return;setBusy(true);setError("");setResult(null);
 try{setResult(await processSSHLog(file,zone,server,publish))}
 catch(e){setError(e instanceof Error?e.message:"SSH processing failed")}
 finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>SSH Log Validation & Pipeline</h3>
 <p className="muted">Approved OpenSSH logs (up to 1 MiB) · frozen SSH detector · source-IP / five-minute windows. One action runs inference and, when enabled, publishes security-relevant evidence, checks Neo4j and correlation, and runs supported standalone Response and Decision. No raw log retained.</p>
 <form className="eventForm" onSubmit={e=>void submit(e)}>
 <label>Zone<select value={zone} onChange={e=>setZone(e.target.value)}>{zones.map(z=><option key={z.zone_id}>{z.zone_id}</option>)}</select></label>
 <label>Server<select value={server} onChange={e=>setServer(e.target.value)}>{servers.map(x=><option key={x}>{x}</option>)}</select></label>
 <label className="eventFormWide">OpenSSH log<input type="file" accept=".log,.txt,text/plain" required onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null)}}/></label>
 <label className="eventFormWide retentionLabel"><input type="checkbox" checked={publish} onChange={e=>setPublish(e.target.checked)}/> Share security-relevant assessments to Monitoring Feed and run supported pipeline stages</label>
 <button disabled={!file||!server||busy}>{busy?"Processing SSH log…":"Process SSH Log"}</button></form>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>Frozen SSH detector results</h4>
 <p>Parsed: {result.parsed_count} · Windows: {result.assessment_count} · Security-relevant: {result.security_relevant_count}</p>
 {result.truncated&&<p className="muted">Processing limited to 100 security-relevant windows; remaining windows not published.</p>}
 <p>{!publish?"Preview only":result.events.length?result.events.filter(x=>x.status==="DECISION_COMPLETE").length+" Decision(s) completed out of "+result.events.length+" published events":"No security-relevant events to publish"}</p>
 {result.assessments.map((a,i)=><details className="sshWindow" key={i}><summary>{a.evidence_state.replaceAll("_"," ")} · {a.source_ip??"Unknown source"} · {a.window_start??"Unknown time"}</summary>
 <div className="sshWindowBody"><p>Source IP: {a.source_ip??"Not available"} · Usernames: {a.usernames.join(", ")||"Not available"}</p><p>Detector votes: {a.detector_votes}</p><pre className="ppeJson">{JSON.stringify(a.evidence,null,2)}</pre>
 {result.events.find(x=>x.assessment_index===i)&&<div><p>Processing status: <b>{result.events[i].status.replaceAll("_"," ")}</b></p>
 {result.events[i].decision&&<p>Decision: {result.events[i].decision.severity} · {result.events[i].decision.incident_status}</p>}
 {result.events[i].stages.map((stage,j)=><p key={j}>{stage.stage}: {stage.status}{stage.detail?" · "+stage.detail:""}</p>)}</div>}
 </div></details>)}
 <p className="muted">Original event timestamps remain distinct from receipt time. Correlated events require a validated multi-domain Response/Decision workflow; they are not silently assigned standalone severity.</p>
 </div>}{result?.published&&result.events.length>0&&<PostPublicationCheck kind="ssh" ids={result.events.map(e=>e.event_id)}/> }</section>;
}
