import {useEffect,useState} from "react";
import {getSavedSSHDecision,getOperationalDecision,reevaluateDecision,type DecisionInputReview,type DecisionReevaluation} from "./api";

type View={decision:{severity:string|null;incident_status:string};original_decision?:{severity:string|null};reevaluation?:DecisionReevaluation|null;input_review?:DecisionInputReview};
const label=(s:string|null|undefined)=>s??"NO SEVERITY";

export default function DecisionReviewNotice({kind,id,onChanged}:{kind:"ssh"|"operations";id:string;onChanged?:()=>void}){
 const [view,setView]=useState<View|null>(null);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const load=()=>(kind==="ssh"?getSavedSSHDecision(id):getOperationalDecision(id)).then(v=>setView(v as View)).catch(()=>setView(null));
 useEffect(()=>{setView(null);setError("");void load()},[kind,id]);
 if(!view?.input_review)return null;
 const review=view.input_review;
 async function reevaluate(){
  setBusy(true);setError("");
  try{await reevaluateDecision(kind,id);await load();onChanged?.()}
  catch(e){setError(e instanceof Error&&e.message.includes("(403)")?"Only Decision authorities (administrators) can re-evaluate.":e instanceof Error?e.message:"Re-evaluation unavailable")}
  finally{setBusy(false)}
 }
 const changed=review.changed_inputs.map(key=>{const input=review.current_inputs[key];return key.split(":")[0].toUpperCase()+" → "+(input?.status??"detector result").replaceAll("_"," ")});
 return <div className={`decisionReviewNotice ${review.reevaluation_required?"decisionReviewPending":""}`} role="status">
  {review.reevaluation_required&&<><p><b>⚠ Human verdict changed a Decision input</b> ({changed.join(", ")}). The current Decision ({label(view.decision.severity)}) was based on the earlier input.</p>
   <button type="button" disabled={busy} onClick={()=>void reevaluate()}>{busy?"Re-evaluating…":"Re-evaluate with human-verified inputs"}</button>
   <p className="muted">Re-runs the same deterministic Decision rules on the human-verified inputs. No AI call; the original Decision stays in history.</p></>}
  {view.reevaluation&&<p className="muted">Re-evaluated {new Date(view.reevaluation.evaluated_at).toLocaleString()} by {view.reevaluation.evaluated_by} on human-verified inputs · current: <b>{label(view.decision.severity)}</b> ({view.decision.incident_status.replaceAll("_"," ")}) · original detector-based severity: <b>{label(view.original_decision?.severity)}</b></p>}
  {error&&<p role="alert" className="error">{error}</p>}
 </div>;
}
