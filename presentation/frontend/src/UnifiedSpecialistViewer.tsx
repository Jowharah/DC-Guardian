import {useEffect,useState} from "react";
import {getUnifiedSpecialists,evaluateUnifiedSpecialists,getUnifiedSynthesis,type UnifiedSynthesisResult,type UnifiedSpecialistResult} from "./api";

export default function UnifiedSpecialistViewer({id}:{id:string}){
 const [saved,setSaved]=useState<UnifiedSpecialistResult|null>(null);
 const [synthesis,setSynthesis]=useState<UnifiedSynthesisResult|null>(null);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 useEffect(()=>{
   let active=true;setSaved(null);setSynthesis(null);setMessage("");
   getUnifiedSynthesis(id).then(x=>{if(active)setSynthesis(x)}).catch(()=>{});
   getUnifiedSpecialists(id).then(x=>{if(active)setSaved(x)})
     .catch(()=>{if(active)setMessage("No saved unified specialist assessment. Evaluation is available below.")});
   return()=>{active=false};
 },[id]);
 async function evaluate(){
   setBusy(true);setMessage("");
   try{setSaved(await evaluateUnifiedSpecialists(id));setSynthesis(await getUnifiedSynthesis(id))}
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
   {synthesis&&<div className="evidenceItem"><h4>Unified Specialist Synthesis · {synthesis.synthesis.grounding_status}</h4>
   <p>{synthesis.synthesis.assessment}</p>
   <h4>Contributing specialists</h4><p>{synthesis.synthesis.contributing_specialists.join(" + ")}</p>
   <h4>Supported source findings</h4><ul>{synthesis.synthesis.supported_source_findings.map((v,i)=><li key={i}>{v.specialist}: {v.finding}</li>)}</ul>
   <h4>Contextual links</h4><ul>{synthesis.synthesis.validated_contextual_links.map((v,i)=><li key={i}>{v.type} · {v.source_id}</li>)}</ul>
   <p className="muted">No verified identity-to-SSH or person-to-PPE attribution. No causal finding or unified severity.</p></div>}
   <p className="muted">Unified Decision: NOT RUN · No validated unified severity rule · Autonomous action disabled.</p>
 </section>;
}
