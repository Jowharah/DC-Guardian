import {useEffect,useState} from "react";
import {getUnifiedHumanReviews,submitUnifiedHumanReview,type HumanReviewRecord} from "./api";
type Outcome=HumanReviewRecord["outcome"];
export default function UnifiedHumanReviewForm({id,canSubmit}:{id:string;canSubmit:boolean}){
 const [records,setRecords]=useState<HumanReviewRecord[]>([]);
 const [outcome,setOutcome]=useState<Outcome>("INCONCLUSIVE");
 const [rationale,setRationale]=useState("");
 const [ack,setAck]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [message,setMessage]=useState("");
 const [historyReady,setHistoryReady]=useState(false);
 useEffect(()=>{let active=true;setHistoryReady(false);getUnifiedHumanReviews(id).then(r=>{if(active){setRecords(r.records);setHistoryReady(true);setError("")}}).catch(()=>{if(active){setHistoryReady(false);setError("Audit history unavailable; submission disabled.")}});return()=>{active=false}},[id]);
 async function submit(){
  if(!canSubmit||!historyReady||!ack||rationale.trim().length<15||busy)return;
  setBusy(true);setError("");setMessage("");
  try{
   await submitUnifiedHumanReview(id,outcome,rationale.trim());
   const history=await getUnifiedHumanReviews(id);
   setRecords(history.records);setMessage("Review recorded in the local audit history.");
   setAck(false);setRationale("");
  }catch(e){setError(e instanceof Error?e.message:"Review could not be recorded")}
  finally{setBusy(false)}
 }
 return <section className="panel reviewFormPanel">
  <h3>Audited human review</h3>
  <p className="muted">Record a human assessment of this unified Evidence group. This does not alter detector Evidence, assign severity, or enable autonomous action.</p>
  <label htmlFor="humanReviewOutcome">Review outcome</label>
  <select id="humanReviewOutcome" value={outcome} disabled={!canSubmit||!historyReady||busy} onChange={e=>setOutcome(e.target.value as Outcome)}>
   <option value="INCONCLUSIVE">Inconclusive</option><option value="NEEDS_FOLLOW_UP">Needs follow-up</option><option value="REVIEWED_NO_FINDING">Reviewed — no finding</option>
  </select>
  <label htmlFor="humanReviewRationale">Reviewer rationale (minimum 15 characters)</label>
  <textarea id="humanReviewRationale" value={rationale} disabled={!canSubmit||!historyReady||busy} maxLength={2000} rows={4} onChange={e=>setRationale(e.target.value)} placeholder="Describe the Evidence reviewed and why you selected this outcome."/>
  <label className="reviewAck"><input type="checkbox" checked={ack} disabled={!canSubmit||!historyReady||busy} onChange={e=>setAck(e.target.checked)}/> I confirm this is my human review of the selected Evidence. The original assessments and Decision remain unchanged.</label>
  <button type="button" disabled={!canSubmit||!historyReady||!ack||rationale.trim().length<15||busy} onClick={()=>void submit()}>{busy?"Saving review…":"Record human review"}</button>
  {!canSubmit&&<p className="muted">A saved deterministic EVIDENCE_REVIEW_REQUIRED result is needed before submission.</p>}
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  <h4>Local audit history · {records.length}</h4>
  {records.length===0?<p className="muted">No recorded human reviews for this group.</p>:<div className="reviewHistory">{records.map(x=><article key={x.audit_id} className="reviewRecord">
   <div className="reviewRecordTop"><b>{x.outcome.replaceAll("_"," ")}</b><span className="reviewStatus">{new Date(x.recorded_at).toLocaleString()}</span></div>
   <p>{x.rationale}</p><p className="muted">Reviewer: {x.reviewer} · Audit: {x.audit_id}</p>
   <details><summary>Audit provenance</summary><code>{x.evidence_signature}</code><p className="muted">Policy: {x.policy_version} · Previous hash: {x.previous_hash}</p></details>
  </article>)}</div>}
 </section>;
}
