import AuditIntegrityPanel from "./AuditIntegrityPanel";
import UnifiedHumanReviewForm from "./UnifiedHumanReviewForm";
import {useEffect,useState} from "react";
import {getUnifiedReviewDecision,getUnifiedHumanReviews,type HumanReviewRecord,type UnifiedReviewDecision} from "./api";
import type {PPEObservation,FaceObservation,UnifiedCorrelationGroup,PublishedSSH,OperationalCorrelation} from "./api";

type Props={ppe:PPEObservation[];face:FaceObservation[];unified:UnifiedCorrelationGroup[];ssh:PublishedSSH[];operational:OperationalCorrelation[];openMonitoring:()=>void};
type QueueItem={id:string;kind:string;zone:string;received:string;state:string;note:string};
export default function HumanReviewQueue({ppe,face,unified,ssh,operational,openMonitoring}:Props){
 const [filter,setFilter]=useState("ALL");
 const [selectedGroup,setSelectedGroup]=useState<string|null>(null);
 const [reviews,setReviews]=useState<Record<string,UnifiedReviewDecision>>({});
 const [reviewErrors,setReviewErrors]=useState<Record<string,boolean>>({});
 const [audit,setAudit]=useState<Record<string,HumanReviewRecord[]>>({});
 const groupIds=unified.map(x=>x.id).sort().join("|");
 useEffect(()=>{
  let active=true;
  const ids=groupIds?groupIds.split("|"):[];
  const refresh=async()=>{
   const settled=await Promise.all(ids.map(async id=>{
    try{return {id,value:await getUnifiedReviewDecision(id),failed:false}}
    catch(e){return {id,value:null,failed:!(e instanceof Error&&e.message.includes("(409)"))}}
   }));
   if(!active)return;
   const saved:Record<string,UnifiedReviewDecision>={};
   const failed:Record<string,boolean>={};
   for(const result of settled){if(result.value)saved[result.id]=result.value;if(result.failed)failed[result.id]=true}
   setReviews(saved);setReviewErrors(failed);
   const history=await Promise.all(ids.map(async id=>{
     try{return {id,records:(await getUnifiedHumanReviews(id)).records}}
     catch{return {id,records:null}}
   }));
   if(!active)return;
   const next:Record<string,HumanReviewRecord[]>={};
   for(const h of history)if(h.records)next[h.id]=h.records;
   setAudit(next);
  };
  void refresh();
  const timer=setInterval(()=>void refresh(),5000);
  return()=>{active=false;clearInterval(timer)};
 },[groupIds]);
 const sources:QueueItem[]=[
  ...ppe.filter(x=>x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,kind:"PPE",zone:x.zone_id,received:x.created_at,state:"AWAITING_SOURCE_REVIEW",note:"Frozen PPE model output; no operator review recorded."})),
  ...face.filter(x=>x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,kind:"FACE",zone:x.zone_id,received:x.created_at,state:"AWAITING_SOURCE_REVIEW",note:"Recognition and zone authorization are independent; no operator review recorded."}))
 ];
 const receipts=new Map<string,string>([
  ...ppe.map(x=>["ppe:"+x.observation_id,x.created_at] as [string,string]),
  ...face.map(x=>["face:"+x.observation_id,x.created_at] as [string,string]),
  ...ssh.map(x=>["ssh:"+x.event_id,x.received_at] as [string,string])
 ]);
 const latest=(id:string)=>audit[id]?.at(-1);
 const candidates:QueueItem[]=unified.map(x=>{
  const times=x.evidence.map(e=>Date.parse(receipts.get(e.kind+":"+e.observation_id)??"")).filter(Number.isFinite);
  return {id:x.id,kind:"UNIFIED",zone:x.zone_id,received:times.length?new Date(Math.max(...times)).toISOString():"",
   state:latest(x.id)?.outcome==="NEEDS_FOLLOW_UP"?"FOLLOW_UP_OUTSTANDING":latest(x.id)?.outcome==="INCONCLUSIVE"?"HUMAN_REVIEW_INCONCLUSIVE":latest(x.id)?.outcome==="REVIEWED_NO_FINDING"?"HUMAN_REVIEW_RECORDED":reviews[x.id]?.decision.status==="EVIDENCE_REVIEW_REQUIRED"?"EVIDENCE_REVIEW_REQUIRED":reviewErrors[x.id]?"REVIEW_STATUS_UNAVAILABLE":"CANDIDATE_ASSESSMENT",note:latest(x.id)?("Human review recorded: "+latest(x.id)!.outcome.replaceAll("_"," ")+". Investigation resolution is not established."):reviews[x.id]?("Saved deterministic disposition · "+reviews[x.id].decision.review_reasons.map(r=>r.replaceAll("_"," ")).join("; ")+". No human completion recorded."):reviewErrors[x.id]?"Review status could not be retrieved; no completion inferred.":"Correlation candidate; no saved grounded review available. No human completion recorded."};
 });
 const decisions:QueueItem[]=[
  ...ssh.filter(x=>x.decision_record?.decision.response_mode==="HUMAN_REVIEW").map(x=>({id:x.event_id,kind:"SSH",zone:x.zone_id,received:x.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved standalone Decision requests human review; no human completion recorded."})),
  ...operational.filter(x=>x.decision?.response_mode==="HUMAN_REVIEW").map(x=>({id:x.id,kind:"OPERATIONS",zone:x.zone_id,received:x.maintenance.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved operational Decision requests human review; no human completion recorded."}))
 ];
 const unique=new Map<string,QueueItem>();
 for(const item of [...sources,...candidates,...decisions])unique.set(item.kind+":"+item.id,item);
 const items=[...unique.values()].filter(x=>filter==="ALL"||x.state===filter).sort((a,b)=>Date.parse(b.received||"1970-01-01")-Date.parse(a.received||"1970-01-01"));
 const counts={source:sources.length,candidate:candidates.filter(x=>x.state==="CANDIDATE_ASSESSMENT").length,unifiedReview:candidates.filter(x=>x.state==="EVIDENCE_REVIEW_REQUIRED").length,decision:decisions.length,recorded:candidates.filter(x=>Boolean(latest(x.id))).length};
 return <section className="analyticsPage">
 <div className="stats"><div className="panel"><small>Source review pending</small><strong>{counts.source}</strong></div><div className="panel"><small>Unified review required</small><strong>{counts.unifiedReview}</strong></div><div className="panel"><small>Decisions requesting review</small><strong>{counts.decision}</strong></div><div className="panel"><small>Groups with recorded human review</small><strong>{counts.recorded}</strong></div></div>
 <section className="panel reviewFilterPanel">
  <div className="analyticsFilterHeader"><div><h3>Review queue</h3><p className="muted">Read-only triage from authorized Evidence feeds. Select a workflow category to inspect its records.</p></div><span className="analyticsFilterMeta">READ-ONLY · HUMAN REVIEW</span></div>
  <div className="analyticsRangeOptions" role="group" aria-label="Review queue category">
   {([{value:"ALL",label:"All items"},{value:"AWAITING_SOURCE_REVIEW",label:"Source review"},{value:"CANDIDATE_ASSESSMENT",label:"Unevaluated candidates"},{value:"EVIDENCE_REVIEW_REQUIRED",label:"Unified review required"},{value:"DECISION_REVIEW_REQUIRED",label:"Decision review"},{value:"FOLLOW_UP_OUTSTANDING",label:"Follow-up outstanding"},{value:"HUMAN_REVIEW_INCONCLUSIVE",label:"Inconclusive"},{value:"HUMAN_REVIEW_RECORDED",label:"Review recorded"}] as const).map(option=><button type="button" key={option.value} className={filter===option.value?"analyticsRangeOption selected":"analyticsRangeOption"} aria-pressed={filter===option.value} onClick={()=>setFilter(option.value)}>{option.label}</button>)}
  </div><p className="muted analyticsFilterNote">Categories describe workflow states, not severity. Human review outcomes are recorded separately from source Evidence.</p>
 </section>
 <section className="panel reviewItemsPanel">
  <div className="analyticsFilterHeader"><div><h3>Review items <span className="reviewItemCount">{items.length}</span></h3><p className="muted">Most recently received Evidence first</p></div></div>
  {items.length===0?<p className="muted">No items returned for this category.</p>:<div className="reviewItemList">{items.map(x=><article key={x.kind+":"+x.id} className="reviewRecord">
   <div className="reviewRecordTop"><div className="reviewRecordTitle"><span className="reviewKind">{x.kind}</span><b>{x.zone}</b></div><span className="reviewStatus">{x.state.replaceAll("_"," ")}</span></div>
   <code className="reviewRecordId">{x.id}</code>
   <p className="reviewRecordNote">{x.note}</p>
   {x.kind==="UNIFIED"&&<button type="button" className="reviewOpenButton" onClick={()=>setSelectedGroup(x.id)}>{selectedGroup===x.id?"Selected for review":"Open review & audit history"}</button>}
   <div className="reviewRecordFooter"><span>Received</span><time dateTime={x.received}>{x.received?new Date(x.received).toLocaleString():"Unavailable"}</time></div>
  </article>)}</div>}
 </section>
 {selectedGroup&&<UnifiedHumanReviewForm key={selectedGroup} id={selectedGroup} canSubmit={reviews[selectedGroup]?.decision.status==="EVIDENCE_REVIEW_REQUIRED"}/>}
 <AuditIntegrityPanel/>
 <p className="muted">Recorded human reviews do not establish investigation resolution, cross-domain severity, or autonomous action. Candidate membership does not attribute SSH or PPE activity to a recognized person.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center for Evidence investigation</button>
 </section>;
}
