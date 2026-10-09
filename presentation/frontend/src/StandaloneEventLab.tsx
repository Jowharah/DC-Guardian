import {useState} from "react";
import {createStandaloneEvent} from "./api";
export default function StandaloneEventLab(){
 const [domain,setDomain]=useState("CYBERSECURITY"),[zone,setZone]=useState("ZONE-B");
 const [state,setState]=useState("REVIEW_REQUIRED"),[title,setTitle]=useState("SSH authentication failures");
 const [asset,setAsset]=useState("SRV-B1-01"),[description,setDescription]=useState("Controlled standalone SSH assessment");
 const [busy,setBusy]=useState(false),[message,setMessage]=useState("");
 async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setMessage("");try{const item=await createStandaloneEvent({domain,zone_id:zone,state,title,asset_id:asset,description});setMessage("Created "+item.event_id+" · open Monitoring Center to investigate")}catch(e){setMessage(e instanceof Error?e.message:"Unable to create event")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>Standalone synthetic evidence event</h3><p className="muted">Creates an explicitly labeled controlled test record, not a detector prediction or Decision incident. No raw SSH logs are fabricated.</p>
 <form className="ppeLab" onSubmit={e=>void submit(e)}>
 <label>Domain <select value={domain} onChange={e=>setDomain(e.target.value)}>{["CYBERSECURITY","ENVIRONMENTAL","MAINTENANCE","SAFETY","PHYSICAL_SECURITY"].map(x=><option key={x}>{x}</option>)}</select></label>
 <label>Zone <select value={zone} onChange={e=>setZone(e.target.value)}>{["ZONE-A","ZONE-B","ZONE-C"].map(x=><option key={x}>{x}</option>)}</select></label>
 <label>Evidence state <input value={state} onChange={e=>setState(e.target.value)} pattern="[A-Z][A-Z0-9_]*" required/></label>
 <label>Title <input value={title} onChange={e=>setTitle(e.target.value)} maxLength={120} required/></label>
 <label>Asset ID <input value={asset} onChange={e=>setAsset(e.target.value)} pattern="[A-Za-z0-9_-]+" required/></label>
 <label>Description <textarea value={description} onChange={e=>setDescription(e.target.value)} maxLength={500}/></label>
 <button disabled={busy}>{busy?"Creating…":"Create synthetic evidence event"}</button>
 </form>{message&&<p role="status">{message}</p>}</section>
}
