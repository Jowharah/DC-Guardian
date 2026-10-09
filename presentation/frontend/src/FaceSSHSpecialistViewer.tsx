import {useState} from "react";
import {evaluateFaceSSHSpecialists,type FaceSSHSpecialistReview} from "./api";
export default function FaceSSHSpecialistViewer({id}:{id:string}){
 const [result,setResult]=useState<FaceSSHSpecialistReview|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 async function run(){
   setBusy(true);setError("");
   try{setResult(await evaluateFaceSSHSpecialists(id))}
   catch(e){setError(e instanceof Error?e.message:"Specialist evaluation unavailable")}
   finally{setBusy(false)}
 }
 return <section className="evidenceItem">
 <h4>Face + Cybersecurity Specialist Analysis</h4>
 <p className="muted">Independent Cybersecurity and Physical Security findings. Camera and test-time declarations are unverified.</p>
 <button type="button" disabled={busy} onClick={()=>void run()}>{busy?"Evaluating…":"Evaluate Specialists and Review"}</button>
 {error&&<p role="alert">{error}</p>}
 {result&&<>
 <p>Evaluated: {new Date(result.evaluated_at).toLocaleString()}</p>
 {Object.entries(result.specialists).map(([name,a])=><div key={name}>
 <h4>{name.replaceAll("_"," ").toUpperCase()} · {a.grounding_status}</h4>
 <p>{a.assessment}</p>
 <h4>Supported findings</h4><ul>{a.supported_findings.filter(Boolean).map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Limitations</h4><ul>{a.limitations.filter(Boolean).map((v,i)=><li key={i}>{v}</li>)}</ul>
 <h4>Approved citations</h4><ul>{a.citations.map((c,i)=><li key={i}>{c.document_id} / {c.chunk_id}</li>)}</ul>
 </div>)}
 <h4>Deterministic Evidence Review · {result.review.status.replaceAll("_"," ")}</h4>
 <p>Zone authorization: {result.authorization.status} · {result.authorization.source}</p>
 <ul>{result.review.reasons.map(x=><li key={x}>{x.replaceAll("_"," ")}</li>)}</ul>
 <p className="muted">Human review only. No verified physical presence, identity-to-SSH attribution, cross-domain severity, or autonomous action.</p>
 </>}
 </section>;
}
