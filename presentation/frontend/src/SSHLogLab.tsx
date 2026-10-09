import {useEffect,useState} from "react";
import {getTopologyOptions,validateSSHLog,type SSHLogResult} from "./api";
export default function SSHLogLab(){
 const [zones,setZones]=useState<{zone_id:string;servers:string[]}[]>([]);
 const [zone,setZone]=useState("ZONE-B"),[server,setServer]=useState("");
 const [file,setFile]=useState<File|null>(null),[result,setResult]=useState<SSHLogResult|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{getTopologyOptions().then(setZones).catch(()=>setError("Topology unavailable"))},[]);
 const servers=zones.find(x=>x.zone_id===zone)?.servers??[];
 useEffect(()=>{setServer(v=>servers.includes(v)?v:servers[0]??"")},[zone,zones]);
 async function run(){if(!file||!server)return;setBusy(true);setError("");setResult(null);try{setResult(await validateSSHLog(file,zone,server))}catch(e){setError(e instanceof Error?e.message:"SSH inference failed")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>SSH log validation</h3><p className="muted">Upload an approved OpenSSH text log (up to 1 MiB). Runs the frozen detector on source-IP / five-minute windows. Preview only: no raw logs retained, no correlation or Decision severity.</p>
 <div className="eventForm"><label>Zone<select value={zone} onChange={e=>setZone(e.target.value)}>{zones.map(z=><option key={z.zone_id}>{z.zone_id}</option>)}</select></label>
 <label>Server<select value={server} onChange={e=>setServer(e.target.value)}>{servers.map(x=><option key={x}>{x}</option>)}</select></label>
 <label className="eventFormWide">OpenSSH log<input type="file" accept=".log,.txt,text/plain" onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null)}}/></label></div>
 <button disabled={!file||!server||busy} onClick={()=>void run()}>{busy?"Running SSH detector…":"Validate SSH log"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>Frozen SSH detector results</h4><p>Parsed: {result.parsed_count} · Windows: {result.assessment_count} · Security-relevant: {result.security_relevant_count}</p>{result.truncated&&<p className="muted">Preview limited to 100 security-relevant windows.</p>}
 {result.assessments.map((a,i)=><details className="sshWindow" key={i}><summary>{a.evidence_state.replaceAll("_"," ")} · {a.window_start??"Unknown time"} · {a.source_ip??"Unknown source"}</summary><div className="sshWindowBody"><p>Source IP: {a.source_ip??"Not available"} · Usernames: {a.usernames.join(", ")||"Not available"}</p><p>Detector votes: {a.detector_votes} · Explicit security signal: {String(a.explicit_security_signal)}</p><pre className="ppeJson">{JSON.stringify(a.evidence,null,2)}</pre></div></details>)}
 <p className="muted">Source: uploaded OpenSSH log · no standalone feed record created in this preview stage.</p></div>}</section>;
}
