import {useEffect,useState} from "react";
import {getEvidenceReview,recordEvidenceReview,type EvidenceReviewEffective,type EvidenceReviewRecord,type EvidenceVerdict,type InvestigatorSingleKind} from "./api";

const STATUS_LABELS:Record<string,string>={COMPLIANT:"Compliant",NON_COMPLIANT:"Non-compliant",AUTHORIZED:"Authorized person",NO_FACE:"No face present",UNAUTHORIZED:"Unauthorized person",UNKNOWN_PERSON:"Unknown person",BENIGN:"Benign activity",ANOMALOUS:"Anomalous activity",HEALTHY:"Healthy drive",AT_RISK:"At risk",NORMAL:"Normal conditions",ABNORMAL:"Abnormal conditions"};
const label=(status:string|null)=>status?(STATUS_LABELS[status]??status.replaceAll("_"," ")):"Not reported";

export default function EvidenceReviewPanel({kind,id}:{kind:InvestigatorSingleKind;id:string}){
 const [records,setRecords]=useState<EvidenceReviewRecord[]>([]);
 const [effective,setEffective]=useState<EvidenceReviewEffective|null>(null);
 const [vocabulary,setVocabulary]=useState<string[]>([]);
 const [verdict,setVerdict]=useState<EvidenceVerdict>("CONFIRMED");
 const [corrected,setCorrected]=useState("");
 const [rationale,setRationale]=useState("");
 const [ack,setAck]=useState(false);
 const [ready,setReady]=useState(false);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 const [message,setMessage]=useState("");
 function load(active:()=>boolean){
  return getEvidenceReview(kind,id).then(r=>{if(!active())return;setRecords(r.records);setEffective(r.effective);setVocabulary(r.vocabulary);setReady(true);setError("")})
   .catch(()=>{if(active()){setReady(false);setError("Review history unavailable; recording is disabled.")}});
 }
 useEffect(()=>{let active=true;setReady(false);setMessage("");void load(()=>active);return()=>{active=false}},[kind,id]);
 const modelStatus=records.at(-1)?.model_status??effective?.model_status??null;
 const needsStatus=verdict==="OVERRIDDEN";
 const options=vocabulary.filter(v=>v!==modelStatus);
 const valid=ready&&ack&&rationale.trim().length>=15&&(!needsStatus||options.includes(corrected));
 async function submit(){
  if(!valid||busy)return;
  setBusy(true);setError("");setMessage("");
  try{
   await recordEvidenceReview(kind,id,{verdict,corrected_status:needsStatus?corrected:null,rationale:rationale.trim(),acknowledgment:true});
   await load(()=>true);
   setMessage("Verdict recorded in the audit chain. The detector output is unchanged.");
   setRationale("");setAck(false);setCorrected("");
  }catch(e){setError(e instanceof Error&&e.message.includes("(403)")?"Your role cannot record verdicts for this Evidence domain or zone.":e instanceof Error?e.message:"Verdict could not be recorded")}
  finally{setBusy(false)}
 }
 return <section className="panel reviewFormPanel">
  <h3>Human verdict</h3>
  {effective?<p><b>{effective.source==="HUMAN_OVERRIDE"?"Human override":effective.verdict==="CONFIRMED"?"Human confirmed":"Human review inconclusive"}:</b> {label(effective.effective_status)}
   {effective.source==="HUMAN_OVERRIDE"&&<> · detector reported {label(effective.model_status)}</>} · {effective.reviewer} · {new Date(effective.recorded_at).toLocaleString()}</p>
   :<p className="muted">No human verdict recorded. Detector result: {label(modelStatus)}.</p>}
  <p className="muted">The detector output stays frozen and visible. A verdict is stored beside it in a tamper-evident audit chain; an override changes whether this event is treated as abnormal for correlation, and the AI Investigator reports both.</p>
  <label htmlFor="evidenceVerdict">Verdict</label>
  <select id="evidenceVerdict" value={verdict} disabled={!ready||busy} onChange={e=>{setVerdict(e.target.value as EvidenceVerdict);setCorrected("")}}>
   <option value="CONFIRMED">Confirm detector result</option><option value="OVERRIDDEN">Override detector result</option><option value="INCONCLUSIVE">Inconclusive</option>
  </select>
  {needsStatus&&<><label htmlFor="evidenceCorrected">Human-verified status</label>
   <select id="evidenceCorrected" value={corrected} disabled={!ready||busy} onChange={e=>setCorrected(e.target.value)}>
    <option value="">Select status…</option>{options.map(v=><option key={v} value={v}>{label(v)}</option>)}
   </select></>}
  <label htmlFor="evidenceRationale">Rationale (minimum 15 characters)</label>
  <textarea id="evidenceRationale" value={rationale} disabled={!ready||busy} maxLength={2000} rows={3} onChange={e=>setRationale(e.target.value)} placeholder="What did you check, and why does the result hold or not hold?"/>
  <label className="reviewAck"><input type="checkbox" checked={ack} disabled={!ready||busy} onChange={e=>setAck(e.target.checked)}/> I confirm this is my own review of this Evidence.</label>
  <button type="button" disabled={!valid||busy} onClick={()=>void submit()}>{busy?"Recording…":"Record verdict"}</button>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  <h4>Verdict history · {records.length}</h4>
  {records.length===0?<p className="muted">No verdicts recorded.</p>:<div className="reviewHistory">{records.slice().reverse().map(x=><article key={x.audit_id} className="reviewRecord">
   <div className="reviewRecordTop"><b>{x.verdict==="OVERRIDDEN"?"Overridden → "+label(x.corrected_status):x.verdict==="CONFIRMED"?"Confirmed":"Inconclusive"}</b><span className="reviewStatus">{new Date(x.recorded_at).toLocaleString()}</span></div>
   <p>{x.rationale}</p><p className="muted">Reviewer: {x.reviewer} · Detector: {label(x.model_status)} · Audit: {x.audit_id}</p>
  </article>)}</div>}
 </section>;
}
