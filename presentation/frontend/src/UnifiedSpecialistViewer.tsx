import {useEffect,useState} from "react";
import {getUnifiedSpecialists,evaluateUnifiedSpecialists,type UnifiedSpecialistResult} from "./api";

export default function UnifiedSpecialistViewer({id}:{id:string}){
 const [saved,setSaved]=useState<UnifiedSpecialistResult|null>(null);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 useEffect(()=>{
   let active=true;setSaved(null);setMessage("");
   getUnifiedSpecialists(id).then(x=>{if(active)setSaved(x)})
     .catch(()=>{if(active)setMessage("No saved unified specialist assessment. Evaluation is available below.")});
   return()=>{active=false};
 },[id]);
 async function evaluate(){
   setBusy(true);setMessage("");
   try{setSaved(await evaluateUnifiedSpecialists(id))}
   catch(e){setMessage(e instanceof Error?e.message:"Specialist evaluation unavailable")}
   finally{setBusy(false)}
 }
 return <section className="evidenceItem">
   <h4>Unified Specialist Agent Analysis</h4>
   <p className="muted">Grounded, domain-scoped Response only. Specialists cannot assign a unified severity or attribute SSH activity to a recognized person.</p>
   <button disabled={busy} onClick={()=>void evaluate()}>{busy?"Evaluating…":saved?"Re-evaluate Specialists":"Evaluate Specialists"}</button>
   {message&&<p role="status">{message}</p>}
   {saved&&<><p>Evaluated: {new Date(saved.evaluated_at).toLocaleString()}</p>
     {Object.entries(saved.specialists).map(([name,a])=><div key={name}>
       <h4>{name.replaceAll("_"," ").toUpperCase()} · {a.grounding_status}</h4>
       <p>{a.assessment}</p>
       <h4>Supported findings</h4><ul>{a.supported_findings.map((v,i)=><li key={i}>{v}</li>)}</ul>
       <h4>Recommended considerations</h4><ul>{a.recommended_considerations.map((v,i)=><li key={i}>{v}</li>)}</ul>
       <h4>Limitations</h4><ul>{a.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul>
       <h4>Approved citations</h4><ul>{a.citations.map((c,i)=><li key={i}>{c.document_id} / {c.chunk_id}</li>)}</ul>
     </div>)}
   </>}
   <p className="muted">Unified Decision: NOT RUN · No validated unified severity rule · Autonomous action disabled.</p>
 </section>;
}
