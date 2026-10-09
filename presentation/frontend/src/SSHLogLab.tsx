import {useEffect,useState} from "react";
import {getTopologyOptions,validateSSHLog,publishSSH,type SSHLogResult} from "./api";
export default function SSHLogLab(){
 const [zones,setZones]=useState<{zone_id:string;servers:string[]}[]>([]);
 const [zone,setZone]=useState("ZONE-B"),[server,setServer]=useState("");
 const [file,setFile]=useState<File|null>(null),[result,setResult]=useState<SSHLogResult|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 const [selected,setSelected]=useState<number[]>([]),[published,setPublished]=useState<number[]>([]),[notice,setNotice]=useState("");
 useEffect(()=>{getTopologyOptions().then(setZones).catch(()=>setError("Topology unavailable"))},[]);
 const servers=zones.find(x=>x.zone_id===zone)?.servers??[];
 useEffect(()=>{setServer(v=>servers.includes(v)?v:servers[0]??"")},[zone,zones]);
 async function run(){if(!file||!server)return;setBusy(true);setError("");setResult(null);setSelected([]);setPublished([]);setNotice("");try{setResult(await validateSSHLog(file,zone,server))}catch(e){setError(e instanceof Error?e.message:"SSH inference failed")}finally{setBusy(false)}}
 async function share(){if(!result||!selected.length)return;setBusy(true);setError("");try{const response=await publishSSH(result.preview_id,selected);setPublished(v=>[...new Set([...v,...selected])]);setSelected([]);setNotice(`Published ${response.published_event_ids.length} SSH assessment(s) to Monitoring Center.`)}catch(e){setError(e instanceof Error?e.message:"Publishing failed")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>SSH log validation</h3><p className="muted">Upload an approved OpenSSH text log (up to 1 MiB). Runs the frozen detector on source-IP / five-minute windows. Preview only: no raw logs retained, no correlation or Decision severity.</p>
 <div className="eventForm"><label>Zone<select value={zone} onChange={e=>setZone(e.target.value)}>{zones.map(z=><option key={z.zone_id}>{z.zone_id}</option>)}</select></label>
 <label>Server<select value={server} onChange={e=>setServer(e.target.value)}>{servers.map(x=><option key={x}>{x}</option>)}</select></label>
 <label className="eventFormWide">OpenSSH log<input type="file" accept=".log,.txt,text/plain" onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null)}}/></label></div>
 <button disabled={!file||!server||busy} onClick={()=>void run()}>{busy?"Running SSH detector…":"Validate SSH log"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>Frozen SSH detector results</h4><p>Parsed: {result.parsed_count} · Windows: {result.assessment_count} · Security-relevant: {result.security_relevant_count}</p>{result.truncated&&<p className="muted">Preview limited to 100 security-relevant windows.</p>}
 {result.assessments.map((a,i)=><div className="sshPublishRow" key={i}><label><input type="checkbox" disabled={busy||published.includes(i)} checked={selected.includes(i)||published.includes(i)} onChange={e=>setSelected(v=>e.target.checked?[...v,i]:v.filter(n=>n!==i))}/> {published.includes(i)?"Published":"Share this assessment"}</label><details className="sshWindow"><summary>{a.evidence_state.replaceAll("_"," ")} · {a.window_start??"Unknown time"} · {a.source_ip??"Unknown source"}</summary><div className="sshWindowBody"><p>Source IP: {a.source_ip??"Not available"} · Usernames: {a.usernames.join(", ")||"Not available"}</p><p>Detector votes: {a.detector_votes} · Explicit security signal: {String(a.explicit_security_signal)}</p><pre className="ppeJson">{JSON.stringify(a.evidence,null,2)}</pre></div></details></div>)}
 <button type="button" disabled={busy||selected.length===0} onClick={()=>void share()}>Share selected to Monitoring Feed</button>{notice&&<p role="status">{notice}</p>}
 <p className="muted">Publishing retains detector assessment metadata, not raw SSH log lines. These remain standalone Evidence, not Decision incidents.</p></div>}</section>;
}
