import {useEffect,useState} from "react";
import {checkPublishedCorrelations,type PublishedCorrelationCheck} from "./api";

export default function PostPublicationCheck({kind,ids}:{kind:string;ids:string[]}){
 const [result,setResult]=useState<PublishedCorrelationCheck|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const key=ids.join("|");
 useEffect(()=>{
   if(!ids.length){setResult(null);return}
   let active=true;setBusy(true);setResult(null);setError("");
   checkPublishedCorrelations(kind,ids).then(r=>{if(active)setResult(r)})
     .catch(e=>{if(active)setError(e instanceof Error?e.message:"Correlation check unavailable")})
     .finally(()=>{if(active)setBusy(false)});
   return()=>{active=false};
 },[kind,key]);
 if(!ids.length)return null;
 return <div className="evidenceItem" aria-live="polite">
  <h4>Automatic correlation check</h4>
  {busy&&<p>Checking previously published Evidence…</p>}
  {error&&<p role="alert">Correlation check unavailable: {error}. Your source Evidence remains stored.</p>}
  {result&&<><p><b>{result.groups.length?"Eligible candidate found":"No eligible correlation found"}</b></p>
   {result.groups.map(g=><div key={g.id}>
     <p><b>{g.domains.join(" + ")}</b> · {g.zone_id} · {g.evidence.length} Evidence records</p>
     <p className="muted">{g.edges.map(e=>e.type).join(" + ")} · Candidate only</p>
   </div>)}
   <p className="muted">{result.note} Open Monitoring Center for the full investigation.</p>
  </>}
 </div>;
}
