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
 <div className="panel analyticsFilterPanel"><h3>Review queue</h3><p className="muted">Read-only triage from authorized Evidence feeds. These categories describe different workflows, not severity. No reviewer action or audit record is created.</p>
 <label htmlFor="reviewQueueFilter">Queue category</label><select id="reviewQueueFilter" value={filter} onChange={e=>setFilter(e.target.value)}>
 <option value="ALL">All categories</option><option value="AWAITING_SOURCE_REVIEW">Awaiting source review</option>
 <option value="CANDIDATE_ASSESSMENT">Unified correlation candidates</option><option value="DECISION_REVIEW_REQUIRED">Saved Decisions requiring human review</option></select></div>
 <div className="panel analyticsDrilldown"><h3>Review items · {items.length}</h3>
 {items.length===0?<p className="muted">No items returned for this category.</p>:<ul>{items.map(x=><li key={x.kind+":"+x.id} className="reviewQueueItem"><div><b>{x.kind} · {x.zone}</b><p><code>{x.id}</code></p><p className="muted">{x.note}</p></div><div><strong>{x.state.replaceAll("_"," ")}</strong><p className="muted">{x.received?new Date(x.received).toLocaleString():"Receipt unavailable"}</p></div></li>)}</ul>}
 </div>
 <p className="muted">No verified human review completion, escalation, cross-domain severity, or autonomous action is inferred. Candidate membership does not attribute SSH or PPE activity to a recognized person.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center for Evidence investigation</button>
 </section>;
}
