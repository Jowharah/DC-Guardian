import {useState} from "react";
import type {PPEObservation,FaceObservation,UnifiedCorrelationGroup,PublishedSSH,OperationalCorrelation} from "./api";

type Props={ppe:PPEObservation[];face:FaceObservation[];unified:UnifiedCorrelationGroup[];ssh:PublishedSSH[];operational:OperationalCorrelation[];openMonitoring:()=>void};
type QueueItem={id:string;kind:string;zone:string;received:string;state:string;note:string};
export default function HumanReviewQueue({ppe,face,unified,ssh,operational,openMonitoring}:Props){
 const [filter,setFilter]=useState("ALL");
 const sources:QueueItem[]=[
  ...ppe.filter(x=>x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,kind:"PPE",zone:x.zone_id,received:x.created_at,state:"AWAITING_SOURCE_REVIEW",note:"Frozen PPE model output; no operator review recorded."})),
  ...face.filter(x=>x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,kind:"FACE",zone:x.zone_id,received:x.created_at,state:"AWAITING_SOURCE_REVIEW",note:"Recognition and zone authorization are independent; no operator review recorded."}))
 ];
 const receipts=new Map<string,string>([
  ...ppe.map(x=>["ppe:"+x.observation_id,x.created_at] as [string,string]),
  ...face.map(x=>["face:"+x.observation_id,x.created_at] as [string,string]),
  ...ssh.map(x=>["ssh:"+x.event_id,x.received_at] as [string,string])
 ]);
 const candidates:QueueItem[]=unified.filter(x=>x.domains.length>=3).map(x=>{
  const times=x.evidence.map(e=>Date.parse(receipts.get(e.kind+":"+e.observation_id)??"")).filter(Number.isFinite);
  return {id:x.id,kind:"UNIFIED",zone:x.zone_id,received:times.length?new Date(Math.max(...times)).toISOString():"",
   state:"CANDIDATE_ASSESSMENT",note:"Correlation candidate. Saved deterministic review status is not queried here; human review completion is unknown."};
 });
 const decisions:QueueItem[]=[
  ...ssh.filter(x=>x.decision_record?.decision.response_mode==="HUMAN_REVIEW").map(x=>({id:x.event_id,kind:"SSH",zone:x.zone_id,received:x.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved standalone Decision requests human review; no human completion recorded."})),
  ...operational.filter(x=>x.decision?.response_mode==="HUMAN_REVIEW").map(x=>({id:x.id,kind:"OPERATIONS",zone:x.zone_id,received:x.maintenance.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved operational Decision requests human review; no human completion recorded."}))
 ];
 const unique=new Map<string,QueueItem>();
 for(const item of [...sources,...candidates,...decisions])unique.set(item.kind+":"+item.id,item);
 const items=[...unique.values()].filter(x=>filter==="ALL"||x.state===filter).sort((a,b)=>Date.parse(b.received||"1970-01-01")-Date.parse(a.received||"1970-01-01"));
 const counts={source:sources.length,candidate:candidates.length,decision:decisions.length};
 return <section className="analyticsPage">
 <div className="stats"><div className="panel"><small>Source review pending</small><strong>{counts.source}</strong></div><div className="panel"><small>Unified candidates</small><strong>{counts.candidate}</strong></div><div className="panel"><small>Decisions requesting review</small><strong>{counts.decision}</strong></div><div className="panel"><small>Human review completions</small><strong>Not tracked</strong></div></div>
 <section className="panel reviewFilterPanel">
  <div className="analyticsFilterHeader"><div><h3>Review queue</h3><p className="muted">Read-only triage from authorized Evidence feeds. Select a workflow category to inspect its records.</p></div><span className="analyticsFilterMeta">READ-ONLY · HUMAN REVIEW</span></div>
  <div className="analyticsRangeOptions" role="group" aria-label="Review queue category">
   {([{value:"ALL",label:"All items"},{value:"AWAITING_SOURCE_REVIEW",label:"Source review"},{value:"CANDIDATE_ASSESSMENT",label:"Unified candidates"},{value:"DECISION_REVIEW_REQUIRED",label:"Decision review"}] as const).map(option=><button type="button" key={option.value} className={filter===option.value?"analyticsRangeOption selected":"analyticsRangeOption"} aria-pressed={filter===option.value} onClick={()=>setFilter(option.value)}>{option.label}</button>)}
  </div><p className="muted analyticsFilterNote">Categories describe workflow states, not severity. No reviewer action or audit record is created.</p>
 </section>
 <section className="panel reviewItemsPanel">
  <div className="analyticsFilterHeader"><div><h3>Review items <span className="reviewItemCount">{items.length}</span></h3><p className="muted">Most recently received Evidence first</p></div></div>
  {items.length===0?<p className="muted">No items returned for this category.</p>:<div className="reviewItemList">{items.map(x=><article key={x.kind+":"+x.id} className="reviewRecord">
   <div className="reviewRecordTop"><div className="reviewRecordTitle"><span className="reviewKind">{x.kind}</span><b>{x.zone}</b></div><span className="reviewStatus">{x.state.replaceAll("_"," ")}</span></div>
   <code className="reviewRecordId">{x.id}</code>
   <p className="reviewRecordNote">{x.note}</p>
   <div className="reviewRecordFooter"><span>Received</span><time dateTime={x.received}>{x.received?new Date(x.received).toLocaleString():"Unavailable"}</time></div>
  </article>)}</div>}
 </section>
 <p className="muted">No verified human review completion, escalation, cross-domain severity, or autonomous action is inferred. Candidate membership does not attribute SSH or PPE activity to a recognized person.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center for Evidence investigation</button>
 </section>;
}
