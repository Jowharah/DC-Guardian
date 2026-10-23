import {useEffect,useState} from "react";
import DateRangeInputs,{dayBounds} from "./DateRange";
import {getUnifiedHumanReviews,type HumanReviewRecord,type LatestEvidenceReview} from "./api";
import type {Incident,PublishedSSH,PPEObservation,FaceObservation,MaintenanceEvent,EnvironmentalEvent,OperationalCorrelation,UnifiedCorrelationGroup} from "./api";
type Props={incidents:Incident[];ssh:PublishedSSH[];ppe:PPEObservation[];face:FaceObservation[];maintenance:MaintenanceEvent[];environment:EnvironmentalEvent[];operational:OperationalCorrelation[];unified:UnifiedCorrelationGroup[];verdicts?:Record<string,LatestEvidenceReview>;decisions?:DecisionRow[];openMonitoring:()=>void;openEvent?:(id:string)=>void};
import {DOMAINS,outcomeRecords as buildOutcomes} from "./detectorOutcomes";
import type {DecisionRow} from "./App";
const words=(value:string)=>value.replaceAll("_"," ");
const palette=["#8564c8","#299eaa","#e0a449","#d76e96","#6592dc"];
function Donut({items,onSelect}:{items:{name:string;value:number}[];onSelect?:(name:string)=>void}){
 const total=items.reduce((a,b)=>a+b.value,0);
 let offset=0;
 return <div className="analyticsDonutLayout"><svg viewBox="0 0 160 160" role="img" aria-label={items.map(x=>x.name+": "+x.value).join(", ")}>
 <circle cx="80" cy="80" r="56" fill="none" stroke="#858595" strokeOpacity=".16" strokeWidth="22"/>
 {items.map((item,i)=>{const share=total?item.value/total:0;const start=offset;offset+=share;return <circle key={item.name} cx="80" cy="80" r="56" fill="none" stroke={palette[i%palette.length]} strokeWidth="22" strokeDasharray={`${share*351.86} 351.86`} strokeDashoffset={-start*351.86} transform="rotate(-90 80 80)"/>})}
 <text x="80" y="77" textAnchor="middle" fontSize="26" fontWeight="700" fill="currentColor">{total}</text><text x="80" y="94" textAnchor="middle" fontSize="10" fill="currentColor">Records</text></svg>
 <div className="analyticsLegend">{items.map((item,i)=><button type="button" key={item.name} disabled={!onSelect||!item.value} onClick={()=>onSelect?.(item.name)}><span style={{background:palette[i%palette.length]}}/><span>{item.name}</span><b>{item.value}</b></button>)}</div></div>
}
function Bars({items,onSelect}:{items:{name:string;value:number}[];onSelect?:(name:string)=>void}){
 const max=Math.max(1,...items.map(x=>x.value));
 return <div className="analyticsBars">{items.map((item,i)=><button type="button" key={item.name} className="analyticsBarRow" disabled={!onSelect||!item.value} onClick={()=>onSelect?.(item.name)}><span>{item.name}</span><div className="analyticsTrack"><div style={{width:`${item.value/max*100}%`,background:palette[i%palette.length]}}/></div><b>{item.value}</b></button>)}</div>
}
export default function AnalyticsDashboard({incidents,ssh,ppe,face,maintenance,environment,operational,unified,verdicts={},decisions:allDecisions=[],openMonitoring,openEvent}:Props){

 const [range,setRange]=useState("all");
 const [customFrom,setCustomFrom]=useState("");
 const [customTo,setCustomTo]=useState("");
 const [audit,setAudit]=useState<Record<string,HumanReviewRecord[]>>({});
 const [auditUnavailable,setAuditUnavailable]=useState<string[]>([]);
 const groupIds=unified.map(g=>g.id).sort().join("|");
 useEffect(()=>{
   let active=true;
   const ids=groupIds?groupIds.split("|"):[];
   const refresh=async()=>{
     const responses=await Promise.all(ids.map(async id=>{
       try{return {id,records:(await getUnifiedHumanReviews(id)).records}}
       catch{return {id,records:null}}
     }));
     if(!active)return;
     const records:Record<string,HumanReviewRecord[]>={};
     const unavailable:string[]=[];
     for(const response of responses){
       if(response.records)records[response.id]=response.records;
       else unavailable.push(response.id);
     }
     setAudit(records);setAuditUnavailable(unavailable);
   };
   void refresh();
   const timer=setInterval(()=>void refresh(),5000);
   return()=>{active=false;clearInterval(timer)};
 },[groupIds]);

 const [selection,setSelection]=useState<{type:"domain"|"severity"|"zone"|"correlation"|"review"|"outcome";value:string}|null>(null);
 const cutoff=range==="all"?-Infinity:Date.now()-({"24h":1,"7d":7,"30d":30}[range]??0)*86400000;
 const custom=range==="custom"?dayBounds(customFrom,customTo):null;
 const valid=(value:string|null|undefined)=>{const t=Date.parse(value??"");return Number.isFinite(t)&&t<=Date.now()&&(custom?t>=custom.lower&&t<=custom.upper:t>=cutoff)};
 const sources=[
  ...ssh.map(x=>({id:x.event_id,kind:"Cybersecurity",zone:x.zone_id,time:x.received_at})),
  ...ppe.map(x=>({id:x.observation_id,kind:"Safety / PPE",zone:x.zone_id,time:x.created_at})),
  ...face.map(x=>({id:x.observation_id,kind:"Physical Security",zone:x.zone_id,time:x.created_at})),
  ...maintenance.map(x=>({id:x.event_id,kind:"Maintenance",zone:x.zone_id,time:x.received_at})),
  ...environment.map(x=>({id:x.event_id,kind:"Environmental",zone:x.zone_id,time:x.received_at}))
 ].filter(x=>valid(x.time));
 // Detector result per published record, with any recorded human verdict beside it (shared with Monitoring Center).
 const outcomeRecords=buildOutcomes({ssh,ppe,face,maintenance,environment},verdicts).filter(x=>valid(x.time));
 const outcomeDomains=DOMAINS.map(domain=>{
  const records=outcomeRecords.filter(x=>x.domain===domain);
  const states=new Map<string,number>();
  for(const r of records)states.set(r.state,(states.get(r.state)??0)+1);
  const count=(v:string)=>records.filter(r=>r.verdict?.verdict===v).length;
  return {domain,total:records.length,abnormal:records.filter(r=>r.abnormal).length,
   states:[...states].sort((a,b)=>b[1]-a[1]).map(([state,value])=>({name:words(state),value,state})),
   confirmed:count("CONFIRMED"),overridden:count("OVERRIDDEN"),inconclusive:count("INCONCLUSIVE")};
 });
 const abnormalTotal=outcomeDomains.reduce((a,b)=>a+b.abnormal,0);
 const verdictTotal=outcomeRecords.filter(x=>x.verdict).length;
 const domains=["Cybersecurity","Safety / PPE","Physical Security","Maintenance","Environmental"].map(name=>({name,value:sources.filter(x=>x.kind===name).length}));
 const decisions=allDecisions.filter(x=>valid(x.time)).map(x=>x.severity);
 const received=new Map<string,string>([
  ...ssh.map(x=>["ssh:"+x.event_id,x.received_at] as [string,string]),
  ...ppe.map(x=>["ppe:"+x.observation_id,x.created_at] as [string,string]),
  ...face.map(x=>["face:"+x.observation_id,x.created_at] as [string,string])]);
 const candidateTime=(g:UnifiedCorrelationGroup)=>{const times=g.evidence.map(e=>Date.parse(received.get(e.kind+":"+e.observation_id)??"")).filter(Number.isFinite);return times.length?new Date(Math.max(...times)).toISOString():undefined};
 const severity=[{name:"HIGH",value:decisions.filter(x=>x==="HIGH").length},{name:"MEDIUM",value:decisions.filter(x=>x==="MEDIUM").length},{name:"LOW",value:decisions.filter(x=>x==="LOW").length}];
 const candidates=unified.filter(x=>valid(candidateTime(x)));
 const combinations=new Map<string,number>();
 for(const group of candidates){const name=group.domains.join(" + ");combinations.set(name,(combinations.get(name)??0)+1)}
 const correlationBars=[...combinations].map(([name,value])=>({name,value}));
 const zoneCounts=new Map<string,number>();
 for(const item of sources)zoneCounts.set(item.zone,(zoneCounts.get(item.zone)??0)+1);
 const zones=[...zoneCounts].sort(([a],[b])=>a.localeCompare(b)).map(([name,value])=>({name,value}));
 const sourceTotal=domains.reduce((a,b)=>a+b.value,0);
 const decisionRows=allDecisions.filter(x=>valid(x.time)).map(x=>({id:x.id,kind:x.kind+" · "+x.policy,severity:x.severity}));

 // These are separate workflow populations, not mutually exclusive incident severities.
 // A candidate is never interpreted as a completed review or assigned Decision.
 const pendingObservations=[
   ...ppe.filter(x=>valid(x.created_at)&&x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,detail:"PPE · "+x.zone_id+" · Awaiting source review"})),
   ...face.filter(x=>valid(x.created_at)&&x.review_status==="NOT_REVIEWED").map(x=>({id:x.observation_id,detail:"Face · "+x.zone_id+" · Awaiting source review"}))
 ];
 const otherObservations=[
   ...ppe.filter(x=>valid(x.created_at)&&x.review_status!=="NOT_REVIEWED").map(x=>({id:x.observation_id,detail:"PPE · "+x.zone_id+" · "+x.review_status})),
   ...face.filter(x=>valid(x.created_at)&&x.review_status!=="NOT_REVIEWED").map(x=>({id:x.observation_id,detail:"Face · "+x.zone_id+" · "+x.review_status}))
 ];
 const latestAudit=(id:string)=>audit[id]?.at(-1);
 const withOutcome=(outcome:HumanReviewRecord["outcome"])=>candidates.filter(x=>latestAudit(x.id)?.outcome===outcome).map(x=>({
  id:x.id,detail:x.zone_id+" · "+outcome.replaceAll("_"," ")+" · Human review recorded"
 }));
 const reviewRows={
  "Awaiting source review":pendingObservations,
  "Other source review states":otherObservations,
  "Unified candidates without recorded human review":candidates.filter(x=>!latestAudit(x.id)&&!auditUnavailable.includes(x.id)).map(x=>({id:x.id,detail:x.zone_id+" · No human review record; deterministic review status not assessed here"})),
  "Follow-up outstanding":withOutcome("NEEDS_FOLLOW_UP"),
  "Human review inconclusive":withOutcome("INCONCLUSIVE"),
  "Human review recorded — no finding":withOutcome("REVIEWED_NO_FINDING"),
  "Review history unavailable":candidates.filter(x=>auditUnavailable.includes(x.id)).map(x=>({id:x.id,detail:x.zone_id+" · Audit history unavailable"})),
  "Decisions":decisionRows.map(x=>({id:x.id,detail:x.kind+" · "+x.severity}))
 };
 const reviewCounts=Object.entries(reviewRows).map(([name,rows])=>({name,value:rows.length}));
 const detailRows=selection?.type==="domain"?sources.filter(x=>x.kind===selection.value).map(x=>({id:x.id,detail:x.zone+" · "+new Date(x.time).toLocaleString()})):
 selection?.type==="zone"?sources.filter(x=>x.zone===selection.value).map(x=>({id:x.id,detail:x.kind+" · "+new Date(x.time).toLocaleString()})):
 selection?.type==="severity"?decisionRows.filter(x=>x.severity===selection.value).map(x=>({id:x.id,detail:x.kind+" · "+x.severity})):
 selection?.type==="correlation"?candidates.filter(x=>x.domains.join(" + ")===selection.value).map(x=>({id:x.id,detail:x.zone_id+" · "+x.evidence.length+" Evidence records"})):
 selection?.type==="review"?(reviewRows[selection.value as keyof typeof reviewRows]??[]):
 selection?.type==="outcome"?outcomeRecords.filter(x=>x.domain+" · "+words(x.state)===selection.value).map(x=>({id:x.id,detail:x.zone+" · Detector: "+words(x.state)+(x.verdict?" · Human: "+(x.verdict.verdict==="OVERRIDDEN"?"override → "+words(x.verdict.corrected_status??""):x.verdict.verdict.toLowerCase()):" · No human verdict")})):[];

 const daily=new Map<string,number>();
 for(const x of sources){const day=new Date(x.time).toLocaleDateString();daily.set(day,(daily.get(day)??0)+1)}
 const timeline=[...daily].sort((a,b)=>Date.parse(a[0])-Date.parse(b[0])).map(([name,value])=>({name,value}));
 return <section className="analyticsPage">
 <section className="panel analyticsFilterPanel" aria-label="Analytics time filters">
  <div className="analyticsFilterHeader"><div><h3>Reporting period</h3><p className="muted">Explore activity using Evidence receipt time.</p></div><span className="analyticsFilterMeta">READ-ONLY · LIVE DATA</span></div>
  <div className="analyticsRangeOptions" role="group" aria-label="Receipt time range">
   {([{value:"24h",label:"24 hours"},{value:"7d",label:"7 days"},{value:"30d",label:"30 days"},{value:"all",label:"All available"}] as const).map(option=><button key={option.value} type="button" className={range===option.value?"analyticsRangeOption selected":"analyticsRangeOption"} aria-pressed={range===option.value} onClick={()=>{setRange(option.value);setCustomFrom("");setCustomTo("")}}>{option.label}</button>)}<DateRangeInputs label="Custom dates:" from={customFrom} to={customTo} onChange={(f,t)=>{setCustomFrom(f);setCustomTo(t);setRange(f||t?"custom":"all")}}/>
  </div>
  <p className="muted analyticsFilterNote">Filters use receipt timestamps, not declared capture times. Authorized feed limits still apply.</p>
 </section>
 <div className="stats"><div className="panel"><small>Published source Evidence</small><strong>{sourceTotal}</strong></div><div className="panel"><small>Decisions</small><strong>{decisions.length}</strong></div><div className="panel"><small>Unified candidates</small><strong>{candidates.length}</strong></div><div className="panel"><small>Abnormal detector results</small><strong>{abnormalTotal}</strong></div><div className="panel"><small>Human verdicts recorded</small><strong>{verdictTotal}</strong></div><div className="panel"><small>Observed zones</small><strong>{zones.length}</strong></div></div>
 <section className="panel"><h3>Detector outcomes by domain</h3><p className="muted">What each frozen detector reported, per published record. Human verdicts are counted beside the detector result and do not replace it. Not severities or incidents.</p>
  <div className="analyticsOutcomes">{outcomeDomains.map(d=><div key={d.domain} className="analyticsOutcome"><h4>{d.domain}</h4><p className="muted">{d.total} records · {d.abnormal} abnormal{d.total?` (${Math.round(d.abnormal/d.total*100)}%)`:""}</p>
   {d.states.length?<Bars items={d.states.map(s=>({name:s.name,value:s.value}))} onSelect={value=>setSelection({type:"outcome",value:d.domain+" · "+value})}/>:<p className="muted">No records in this range.</p>}
   <p className="muted analyticsVerdicts">Human: {d.confirmed} confirmed · {d.overridden} overridden · {d.inconclusive} inconclusive</p></div>)}</div>
 </section>
 <div className="analyticsGrid">
 <section className="panel"><h3>Evidence by domain</h3><p className="muted">Published source records; not incidents or Decisions.</p><Donut items={domains} onSelect={value=>setSelection({type:"domain",value})}/></section>
 <section className="panel"><h3>Decision severity</h3><p className="muted">Deterministic Decisions only: saved v1 Decisions plus v2 group and single-event Decisions (a correlated event counts once, with its group). Specialists never assign severity.</p><Donut items={severity} onSelect={value=>setSelection({type:"severity",value})}/></section>
 <section className="panel"><h3>Multi-domain correlation candidates</h3><p className="muted">One count per unified group; pairwise links inside groups are not counted as separate incidents.</p>{correlationBars.length?<Bars items={correlationBars} onSelect={value=>setSelection({type:"correlation",value})}/>:<p className="muted">No unified groups available.</p>}</section>
 <section className="panel"><h3>Evidence by zone</h3><p className="muted">Published source Evidence counts by declared zone.</p>{zones.length?<Bars items={zones} onSelect={value=>setSelection({type:"zone",value})}/>:<p className="muted">No source Evidence available.</p>}</section>
 <section className="panel"><h3>Review & workflow status</h3><p className="muted">Source-review states, recorded human outcomes, and saved severity Decisions are separate workflow populations. Follow-up is not investigation resolution.</p><Bars items={reviewCounts} onSelect={value=>setSelection({type:"review",value})}/></section>
 <section className="panel"><h3>Evidence receipt activity</h3><p className="muted">Published Evidence by local receipt date.</p>{timeline.length?<Bars items={timeline}/>:<p className="muted">No Evidence received in this range.</p>}</section>
 </div>
 {selection&&<section className="panel analyticsDrilldown" aria-live="polite"><div className="analyticsFilterHeader"><div><h3>{selection.value}</h3><p className="muted">{selection.type.toUpperCase()} · {detailRows.length} matching authorized records</p></div><button type="button" className="analyticsClear" onClick={()=>setSelection(null)}>Clear selection</button></div>
 <ul>{detailRows.map(x=><li key={x.id}>{openEvent?<button type="button" className="linkButton analyticsEventLink" onClick={()=>openEvent(x.id)} title="Open this record in the Monitoring Center"><code>{x.id}</code></button>:<code>{x.id}</code>}<span>{x.detail}</span></li>)}</ul>
 <p className="muted">Select an identifier to open that record in the Monitoring Center. Identifiers and statuses are read-only.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center</button></section>}
 <p className="muted">Read-only analytics from authorized feed APIs, refreshed with Monitoring Center every five seconds. Feed limits and RBAC may affect totals. No inference of identity, causation or unified severity.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center</button>
 </section>;
}
