import {useEffect,useState} from "react";
import {getPhysicalSpecialist,evaluatePhysicalSpecialist,type PhysicalSpecialistResult} from "./api";
export default function PhysicalSpecialistViewer({id}:{id:string}){
 const [saved,setSaved]=useState<PhysicalSpecialistResult|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 useEffect(()=>{let active=true;setSaved(null);setError("");
 getPhysicalSpecialist(id).then(v=>{if(active)setSaved(v)}).catch(e=>{
 if(active&&!(e instanceof Error&&e.message.includes("(404)")))setError("Saved specialist lookup unavailable");
 });return()=>{active=false}},[id]);
 async function evaluate(){setBusy(true);setError("");
 try{setSaved(await evaluatePhysicalSpecialist(id))}
 catch(e){setError(e instanceof Error?e.message:"Specialist unavailable")}
 finally{setBusy(false)}}
 return <section className="evidenceItem"><h4>Physical Security Specialist</h4>
 <p className="muted">Grounded source analysis only. No identity-to-PPE association, severity, or autonomous action.</p>
 <button disabled={busy} onClick={()=>void evaluate()}>{busy?"Evaluating…":saved?"Re-evaluate Specialist":"Run Physical Security Specialist"}</button>
 {error&&<p role="alert">{error}</p>}
 {saved&&<><p><b>Grounding: {saved.specialist.grounding_status}</b> · Evaluated: {new Date(saved.evaluated_at).toLocaleString()}</p>
 <p>{saved.specialist.assessment}</p>
 <h4>Supported findings</h4><ul>{saved.specialist.supported_findings.map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Recommended considerations</h4><ul>{saved.specialist.recommended_considerations.map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Limitations</h4><ul>{saved.specialist.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Approved citations</h4><ul>{saved.specialist.citations.map((v,i)=><li key={i}>{v.document_id} / {v.chunk_id}</li>)}</ul></>}
 <p className="muted">Decision: NOT RUN · Physical PPE correlation severity rule not validated under Decision v1.</p>
 </section>
}
