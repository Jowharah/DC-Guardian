import AuditIntegrityPanel from "./AuditIntegrityPanel";
import UnifiedHumanReviewForm from "./UnifiedHumanReviewForm";
import EvidenceReviewPanel from "./EvidenceReviewPanel";
import {useEffect,useState} from "react";
import {getUnifiedReviewDecision,getUnifiedHumanReviews,getLatestEvidenceReviews,type HumanReviewRecord,type UnifiedReviewDecision,type LatestEvidenceReview,type InvestigatorSingleKind,type MaintenanceEvent,type EnvironmentalEvent} from "./api";
import type {PPEObservation,FaceObservation,UnifiedCorrelationGroup,PublishedSSH,OperationalCorrelation} from "./api";

type Props={ppe:PPEObservation[];face:FaceObservation[];unified:UnifiedCorrelationGroup[];ssh:PublishedSSH[];operational:OperationalCorrelation[];maintenance:MaintenanceEvent[];environment:EnvironmentalEvent[];openMonitoring:()=>void;openEvent?:(id:string)=>void};
// Usability study (P01, P03): eleven category tabs were too many. Three status tabs instead;
// the detailed workflow category stays on each item as a tag.
type Bucket="TODO"|"IN_PROGRESS"|"DONE";
const STATUS:Record<string,{bucket:Bucket;label:string}>={
 AWAITING_SOURCE_REVIEW:{bucket:"TODO",label:"Not reviewed"},
 CANDIDATE_ASSESSMENT:{bucket:"TODO",label:"Specialists not run"},
 EVIDENCE_REVIEW_REQUIRED:{bucket:"TODO",label:"Group review needed"},
 DECISION_REVIEW_REQUIRED:{bucket:"TODO",label:"Decision review needed"},
 MEMBER_VERDICT_CHANGED:{bucket:"TODO",label:"Re-review: an event verdict changed"},
 REVIEW_STATUS_UNAVAILABLE:{bucket:"TODO",label:"Review status unavailable"},
 FOLLOW_UP_OUTSTANDING:{bucket:"IN_PROGRESS",label:"Follow-up outstanding"},
 HUMAN_REVIEW_INCONCLUSIVE:{bucket:"IN_PROGRESS",label:"Inconclusive: needs another look"},
 HUMAN_CONFIRMED:{bucket:"DONE",label:"Human confirmed"},
 HUMAN_OVERRIDDEN:{bucket:"DONE",label:"Human override"},
 HUMAN_REVIEW_RECORDED:{bucket:"DONE",label:"Group review recorded"},
};
const bucketOf=(state:string):Bucket=>STATUS[state]?.bucket??"TODO";
const TABS:{value:Bucket|"ALL";label:string}[]=[{value:"TODO",label:"To do"},{value:"IN_PROGRESS",label:"In progress"},{value:"DONE",label:"Completed"},{value:"ALL",label:"All"}];
type QueueItem={id:string;kind:string;zone:string;received:string;state:string;note:string;evidenceKind?:InvestigatorSingleKind};
export default function HumanReviewQueue({ppe,face,unified,ssh,operational,maintenance,environment,openMonitoring,openEvent}:Props){
 const [tab,setTab]=useState<Bucket|"ALL">("TODO");
 const [typeFilter,setTypeFilter]=useState("ALL");
 const [selectedGroup,setSelectedGroup]=useState<string|null>(null);
 const [selectedEvidence,setSelectedEvidence]=useState<{kind:InvestigatorSingleKind;id:string}|null>(null);
 const [verdicts,setVerdicts]=useState<Record<string,LatestEvidenceReview>>({});
 useEffect(()=>{let active=true;const refresh=()=>getLatestEvidenceReviews().then(items=>{if(active)setVerdicts(Object.fromEntries(items.map(v=>[v.kind+":"+v.evidence_id,v])))}).catch(()=>{});void refresh();const timer=setInterval(refresh,5000);return()=>{active=false;clearInterval(timer)}},[]);
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
 const sourceItem=(evidenceKind:InvestigatorSingleKind,id:string,zone:string,received:string,pending:string):QueueItem=>{
  const v=verdicts[evidenceKind+":"+id];
  return {id,kind:evidenceKind.toUpperCase(),zone,received,evidenceKind,
   state:!v?"AWAITING_SOURCE_REVIEW":v.verdict==="OVERRIDDEN"?"HUMAN_OVERRIDDEN":v.verdict==="CONFIRMED"?"HUMAN_CONFIRMED":"HUMAN_REVIEW_INCONCLUSIVE",
   note:!v?pending:v.verdict==="OVERRIDDEN"?`Detector: ${(v.model_status??"not reported").replaceAll("_"," ")} · Human override: ${(v.corrected_status??"").replaceAll("_"," ")} by ${v.reviewer}.`:v.verdict==="CONFIRMED"?`Detector result ${(v.model_status??"").replaceAll("_"," ")} confirmed by ${v.reviewer}.`:`Human review inconclusive (${v.reviewer}); detector result still applies.`};
 };
 const sources:QueueItem[]=[
  ...ppe.map(x=>sourceItem("ppe",x.observation_id,x.zone_id,x.created_at,"Frozen PPE model output; no operator verdict recorded.")),
  ...face.map(x=>sourceItem("face",x.observation_id,x.zone_id,x.created_at,"Recognition and zone authorization are independent; no operator verdict recorded.")),
  ...ssh.map(x=>sourceItem("ssh",x.event_id,x.zone_id,x.received_at,"SSH detector Evidence; no operator verdict recorded.")),
  ...maintenance.map(x=>sourceItem("maintenance",x.event_id,x.zone_id,x.received_at,"SMART failure-risk model output; no operator verdict recorded.")),
  ...environment.map(x=>sourceItem("environment",x.event_id,x.zone_id,x.received_at,"Environmental sensor assessment; no operator verdict recorded."))
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
   state:reviews[x.id]?.member_verdicts_changed_since_review?"MEMBER_VERDICT_CHANGED":latest(x.id)?.outcome==="NEEDS_FOLLOW_UP"?"FOLLOW_UP_OUTSTANDING":latest(x.id)?.outcome==="INCONCLUSIVE"?"HUMAN_REVIEW_INCONCLUSIVE":latest(x.id)?.outcome==="REVIEWED_NO_FINDING"?"HUMAN_REVIEW_RECORDED":reviews[x.id]?.decision.status==="EVIDENCE_REVIEW_REQUIRED"||reviews[x.id]?.decision.status==="REVIEW_REQUIRED"?"EVIDENCE_REVIEW_REQUIRED":reviewErrors[x.id]?"REVIEW_STATUS_UNAVAILABLE":"CANDIDATE_ASSESSMENT",note:reviews[x.id]?.member_verdicts_changed_since_review?"A member Evidence verdict was recorded after the last group review; re-review the group.":latest(x.id)?("Human review recorded: "+latest(x.id)!.outcome.replaceAll("_"," ")+". Investigation resolution is not established."):reviews[x.id]?("Saved deterministic disposition · "+reviews[x.id].decision.review_reasons.map(r=>r.replaceAll("_"," ")).join("; ")+". No human completion recorded."):reviewErrors[x.id]?"Review status could not be retrieved; no completion inferred.":"No current specialist evaluation for this group (never run, or its links changed since the last run). Open it in Monitoring Center and run the unified specialist evaluation (sends this Evidence to OpenAI) to enable human review."};
 });
 const decisions:QueueItem[]=[
  ...ssh.filter(x=>x.decision_record?.decision.response_mode==="HUMAN_REVIEW").map(x=>({id:x.event_id,kind:"SSH",zone:x.zone_id,received:x.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved standalone Decision requests human review; no human completion recorded."})),
  ...operational.filter(x=>x.decision?.response_mode==="HUMAN_REVIEW").map(x=>({id:x.id,kind:"OPERATIONS",zone:x.zone_id,received:x.maintenance.received_at,state:"DECISION_REVIEW_REQUIRED",note:"Saved operational Decision requests human review; no human completion recorded."}))
 ];
 const unique=new Map<string,QueueItem>();
 for(const item of [...sources,...candidates,...decisions])unique.set(item.kind+":"+item.id,item);
 const all=[...unique.values()];
 const kinds=[...new Set(all.map(x=>x.kind))].sort();
 const ofType=all.filter(x=>typeFilter==="ALL"||x.kind===typeFilter);
 const tabCount=(value:Bucket|"ALL")=>ofType.filter(x=>value==="ALL"||bucketOf(x.state)===value).length;
 const items=ofType.filter(x=>tab==="ALL"||bucketOf(x.state)===tab).sort((a,b)=>Date.parse(b.received||"1970-01-01")-Date.parse(a.received||"1970-01-01"));
 const counts={source:sources.filter(x=>x.state==="AWAITING_SOURCE_REVIEW").length,candidate:candidates.filter(x=>x.state==="CANDIDATE_ASSESSMENT").length,unifiedReview:candidates.filter(x=>x.state==="EVIDENCE_REVIEW_REQUIRED").length,decision:decisions.length,recorded:candidates.filter(x=>Boolean(latest(x.id))).length};
 return <section className="analyticsPage">
 <div className="stats"><div className="panel"><small>Source review pending</small><strong>{counts.source}</strong></div><div className="panel"><small>Unified review required</small><strong>{counts.unifiedReview}</strong></div><div className="panel"><small>Decisions requesting review</small><strong>{counts.decision}</strong></div><div className="panel"><small>Groups with recorded human review</small><strong>{counts.recorded}</strong></div></div>
 <section className="panel reviewFilterPanel">
  <div className="analyticsFilterHeader"><div><h3>Review queue</h3><p className="muted">Read-only triage from authorized Evidence feeds. Choose a status, then open an item to review it.</p></div><span className="analyticsFilterMeta">READ-ONLY · HUMAN REVIEW</span></div>
  <div className="queueTabs"><div className="queueTabList" role="tablist" aria-label="Review status">{TABS.map(t=><button type="button" role="tab" key={t.value} aria-selected={tab===t.value} className={tab===t.value?"analyticsRangeOption selected":"analyticsRangeOption"} onClick={()=>setTab(t.value)}>{t.label} <span className="reviewItemCount">{tabCount(t.value)}</span></button>)}</div><label className="queueTypeFilter">Type <select aria-label="Filter by event type" value={typeFilter} onChange={e=>setTypeFilter(e.target.value)}><option value="ALL">All types</option>{kinds.map(k=><option key={k} value={k}>{k}</option>)}</select></label></div><p className="muted analyticsFilterNote">To do: nothing recorded yet. In progress: a human looked but follow-up is open. Completed: a verdict or review is recorded. The tag on each item gives the detailed state, never severity. Human review outcomes are recorded separately from source Evidence.</p>
 </section>
 <section className="panel reviewItemsPanel">
  <div className="analyticsFilterHeader"><div><h3>Review items <span className="reviewItemCount">{items.length}</span></h3><p className="muted">Most recently received Evidence first</p></div></div>
  {items.length===0?<p className="muted">Nothing here for this status and type.</p>:<div className="reviewItemList">{items.map(x=><article key={x.kind+":"+x.id} className="reviewRecord">
   <div className="reviewRecordTop"><div className="reviewRecordTitle"><span className="reviewKind">{x.kind}</span><b>{x.zone}</b></div><span className={`reviewStatus statusTag status-${bucketOf(x.state).toLowerCase()}`}>{STATUS[x.state]?.label??x.state.replaceAll("_"," ")}</span></div>
   <code className="reviewRecordId">{x.id}</code>
   <p className="reviewRecordNote">{x.note}</p>
   {x.kind==="UNIFIED"&&<button type="button" className="reviewOpenButton" onClick={()=>{setSelectedEvidence(null);setSelectedGroup(x.id)}}>{selectedGroup===x.id?"Selected for review":"Open review & audit history"}</button>}
   {x.evidenceKind&&<button type="button" className="reviewOpenButton" onClick={()=>{setSelectedGroup(null);setSelectedEvidence({kind:x.evidenceKind!,id:x.id})}}>{selectedEvidence?.id===x.id?"Selected for review":"Review Evidence & record verdict"}</button>}
   {openEvent&&<button type="button" className="reviewOpenButton reviewMonitorLink" onClick={()=>openEvent(x.id)}>View in Monitoring Center</button>}
   <div className="reviewRecordFooter"><span>Received</span><time dateTime={x.received}>{x.received?new Date(x.received).toLocaleString():"Unavailable"}</time></div>
  </article>)}</div>}
 </section>
 {selectedEvidence&&<EvidenceReviewPanel key={selectedEvidence.kind+":"+selectedEvidence.id} kind={selectedEvidence.kind} id={selectedEvidence.id}/>}
 {selectedGroup&&<UnifiedHumanReviewForm key={selectedGroup} id={selectedGroup} canSubmit={reviews[selectedGroup]?.decision.status==="EVIDENCE_REVIEW_REQUIRED"||reviews[selectedGroup]?.decision.status==="REVIEW_REQUIRED"}/>}
 <AuditIntegrityPanel/>
 <p className="muted">Recorded human reviews do not establish investigation resolution, cross-domain severity, or autonomous action. Candidate membership does not attribute SSH or PPE activity to a recognized person.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center for Evidence investigation</button>
 </section>;
}
