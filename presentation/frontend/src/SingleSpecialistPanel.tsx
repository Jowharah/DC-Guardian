import {useEffect,useState} from "react";
import {evaluateSingleSpecialist,getSingleSpecialist,type SingleSpecialistResult} from "./api";

type Kind="ssh"|"ppe"|"face"|"maintenance"|"environment";
const SPECIALIST:Record<Kind,string>={ssh:"Cybersecurity",ppe:"Physical Security & Safety",face:"Physical Security & Safety",maintenance:"Operations",environment:"Operations"};

/** Consented grounded specialist evaluation for one Evidence record (any domain). */
export default function SingleSpecialistPanel({kind,id}:{kind:Kind;id:string}){
 const [saved,setSaved]=useState<SingleSpecialistResult|null>(null);
 const [consent,setConsent]=useState(false);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 useEffect(()=>{
  let active=true;
  setSaved(null);setMessage("");setConsent(false);
  getSingleSpecialist(kind,id).then(x=>{if(active)setSaved(x)}).catch(()=>{});
  return()=>{active=false};
 },[kind,id]);
 async function run(){
  setBusy(true);setMessage("");
  try{setSaved(await evaluateSingleSpecialist(kind,id));setConsent(false)}
  catch(e){setMessage(e instanceof Error&&e.message.includes("(403)")?"Only administrators can run a specialist evaluation.":
   e instanceof Error?e.message.replace(/^API request failed \(\d+\):? ?/,"Specialist evaluation unavailable. "):"Specialist evaluation unavailable.")}
  finally{setBusy(false)}
 }
 return <section className="panel evidenceItem singleSpecialist" aria-label="Single-event specialist evaluation">
  <h4>Specialist evaluation · {SPECIALIST[kind]}</h4>
  <p className="whoDecides"><b>Who says what:</b> the <b>detector</b> produced the result; this <b>AI specialist only explains it</b> with cited guidance; <b>fixed rules</b> set severity; <b>your human verdict</b> is the review that counts.</p><p className="muted">Grounded in approved knowledge, for this Evidence record alone.</p>
  {saved&&<>
   <p>Evaluated {new Date(saved.evaluated_at).toLocaleString()}{saved.evidence_changed_since&&<b className="staleNote"> · Evidence or human verdict changed since; re-run to update</b>}</p>
   {Object.entries(saved.specialists).map(([name,a])=><details key={name} className="evidenceItem"><summary>{name.replaceAll("_"," ").toUpperCase()} · {a.grounding_status} · View assessment</summary>
    <p>{a.assessment}</p>
    <h5>Supported findings</h5><ul>{a.supported_findings.map((v,i)=><li key={i}>{v}</li>)}</ul>
    <h5>Recommended considerations</h5><ul>{a.recommended_considerations.map((v,i)=><li key={i}>{v}</li>)}</ul>
    <h5>Limitations</h5><ul>{a.limitations.map((v,i)=><li key={i}>{v}</li>)}</ul>
    <h5>Approved citations</h5><ul>{a.citations.map((c,i)=><li key={i}>{c.document_id} / {c.chunk_id}</li>)}</ul>
   </details>)}
  </>}
  <label className="consentLine"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/> I understand this sends this record's saved detector output and any human-verdict summary (no images, no raw logs) to OpenAI.</label>
  <button type="button" disabled={!consent||busy} onClick={()=>void run()}>{busy?"Evaluating… (can take a minute)":saved?"Re-run specialist evaluation":"Run specialist evaluation"}</button>
  {message&&<p role="status">{message}</p>}
 </section>;
}
