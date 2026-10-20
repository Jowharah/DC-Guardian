import {useEffect,useState} from "react";
import {getLifecycle,recordLifecycleTransition,type Lifecycle,type LifecycleAction} from "./api";

const RESOLUTIONS=["NO_FINDING","FALSE_POSITIVE","HANDLED_OUTSIDE_SYSTEM","DUPLICATE"] as const;
const words=(v:string)=>v.replaceAll("_"," ").toLowerCase();

/** Investigation state (open → in review → resolved, reopenable); never changes Evidence or severity. */
export default function LifecyclePanel({subjectType,subjectId}:{subjectType:string;subjectId:string}){
 const [data,setData]=useState<Lifecycle|null>(null);
 const [error,setError]=useState("");
 const [resolution,setResolution]=useState<typeof RESOLUTIONS[number]>("NO_FINDING");
 const [rationale,setRationale]=useState("");
 const [ack,setAck]=useState(false);
 const [busy,setBusy]=useState(false);
 useEffect(()=>{
  let active=true;setData(null);setError("");
  getLifecycle(subjectType,subjectId).then(x=>{if(active)setData(x)})
   .catch(e=>{if(active)setError(e instanceof Error&&e.message.includes("(403)")?"Your role cannot review this item.":"Investigation state unavailable.")});
  return()=>{active=false};
 },[subjectType,subjectId]);
 async function act(action:LifecycleAction){
  setBusy(true);setError("");
  try{setData(await recordLifecycleTransition(subjectType,subjectId,{action,resolution:action==="RESOLVE"?resolution:null,rationale,acknowledgment:ack}));setRationale("");setAck(false)}
  catch(e){setError(e instanceof Error?e.message.replace(/^API request failed \(\d+\):? ?/,""):"Transition failed")}
  finally{setBusy(false)}
 }
 if(!data)return error?<section className="panel evidenceItem" aria-label="Investigation state"><h4>Investigation state</h4><p role="status">{error}</p></section>:null;
 const canStart=["OPEN","REOPENED","REOPENED_EVIDENCE_CHANGED"].includes(data.state);
 return <section className="panel evidenceItem lifecyclePanel" aria-label="Investigation state">
  <h4>Investigation state</h4>
  <p><span className={`severity lifecycle-${data.state.toLowerCase()}`}>{words(data.state).toUpperCase()}</span>{data.assignee&&<> · reviewer {data.assignee}</>}{data.resolution&&<> · {words(data.resolution)}</>}</p>
  {data.state==="REOPENED_EVIDENCE_CHANGED"&&<p className="muted">Evidence or a human verdict changed after this was resolved; review it again.</p>}
  {canStart&&<button type="button" disabled={busy} onClick={()=>void act("START_REVIEW")}>Start review</button>}
  {data.state==="IN_REVIEW"&&<div className="lifecycleForm">
   <label htmlFor="lifecycleResolution">Resolution</label><select id="lifecycleResolution" value={resolution} onChange={e=>setResolution(e.target.value as typeof RESOLUTIONS[number])}>{RESOLUTIONS.map(r=><option key={r} value={r}>{words(r)}</option>)}</select>
   <label htmlFor="lifecycleRationale">Rationale</label><textarea id="lifecycleRationale" value={rationale} onChange={e=>setRationale(e.target.value)} minLength={15} rows={3}/>
   <label className="consentLine"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/> I confirm this resolution is my own review.</label>
   <button type="button" disabled={busy||!ack||rationale.trim().length<15} onClick={()=>void act("RESOLVE")}>Resolve</button>
   {(!ack||rationale.trim().length<15)&&<small className="muted" role="note">To resolve: {rationale.trim().length<15?`write a rationale of at least 15 characters (${rationale.trim().length}/15)`:"rationale complete"}{!ack?" and tick the confirmation above.":"."}</small>}
  </div>}
  {data.state==="RESOLVED"&&<div className="lifecycleForm">
   <label htmlFor="lifecycleReopen">Reason to reopen</label><textarea id="lifecycleReopen" value={rationale} onChange={e=>setRationale(e.target.value)} rows={2}/>
   <button type="button" disabled={busy||rationale.trim().length<15} onClick={()=>void act("REOPEN")}>Reopen</button>
  </div>}
  {error&&<p role="status">{error}</p>}
  {data.transitions.length>0&&<details><summary>History ({data.transitions.length})</summary><ul>{data.transitions.map((t,i)=><li key={i}>{new Date(t.recorded_at).toLocaleString()} · {t.actor} · {words(t.action)} → {words(t.to_state)}{t.resolution?` (${words(t.resolution)})`:""}{t.rationale?` · “${t.rationale}”`:""}</li>)}</ul></details>}
  <p className="muted">{data.note}</p>
 </section>;
}
