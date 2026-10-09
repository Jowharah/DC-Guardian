import {useState} from "react";
import type {Incident,PublishedSSH,PPEObservation,FaceObservation,MaintenanceEvent,EnvironmentalEvent,OperationalCorrelation,UnifiedCorrelationGroup} from "./api";
type Props={incidents:Incident[];ssh:PublishedSSH[];ppe:PPEObservation[];face:FaceObservation[];maintenance:MaintenanceEvent[];environment:EnvironmentalEvent[];operational:OperationalCorrelation[];unified:UnifiedCorrelationGroup[];openMonitoring:()=>void};
const palette=["#8564c8","#299eaa","#e0a449","#d76e96","#6592dc"];
function Donut({items}:{items:{name:string;value:number}[]}){
 const total=items.reduce((a,b)=>a+b.value,0);
 let offset=0;
 return <div className="analyticsDonutLayout"><svg viewBox="0 0 160 160" role="img" aria-label={items.map(x=>x.name+": "+x.value).join(", ")}>
 <circle cx="80" cy="80" r="56" fill="none" stroke="#858595" strokeOpacity=".16" strokeWidth="22"/>
 {items.map((item,i)=>{const share=total?item.value/total:0;const start=offset;offset+=share;return <circle key={item.name} cx="80" cy="80" r="56" fill="none" stroke={palette[i%palette.length]} strokeWidth="22" strokeDasharray={`${share*351.86} 351.86`} strokeDashoffset={-start*351.86} transform="rotate(-90 80 80)"/>})}
 <text x="80" y="77" textAnchor="middle" fontSize="26" fontWeight="700" fill="currentColor">{total}</text><text x="80" y="94" textAnchor="middle" fontSize="10" fill="currentColor">Records</text></svg>
 <div className="analyticsLegend">{items.map((item,i)=><div key={item.name}><span style={{background:palette[i%palette.length]}}/><span>{item.name}</span><b>{item.value}</b></div>)}</div></div>
}
function Bars({items}:{items:{name:string;value:number}[]}){
 const max=Math.max(1,...items.map(x=>x.value));
 return <div className="analyticsBars">{items.map((item,i)=><div key={item.name} className="analyticsBarRow"><span>{item.name}</span><div className="analyticsTrack"><div style={{width:`${item.value/max*100}%`,background:palette[i%palette.length]}}/></div><b>{item.value}</b></div>)}</div>
}
export default function AnalyticsDashboard({incidents,ssh,ppe,face,maintenance,environment,operational,unified,openMonitoring}:Props){

 const [range,setRange]=useState("all");
 const cutoff=range==="all"?-Infinity:Date.now()-({"24h":1,"7d":7,"30d":30}[range]??0)*86400000;
 const valid=(value:string|null|undefined)=>{const t=Date.parse(value??"");return Number.isFinite(t)&&t<=Date.now()&&t>=cutoff};
 const sources=[
  ...ssh.map(x=>({kind:"Cybersecurity",zone:x.zone_id,time:x.received_at})),
  ...ppe.map(x=>({kind:"Safety / PPE",zone:x.zone_id,time:x.created_at})),
  ...face.map(x=>({kind:"Physical Security",zone:x.zone_id,time:x.created_at})),
  ...maintenance.map(x=>({kind:"Maintenance",zone:x.zone_id,time:x.received_at})),
  ...environment.map(x=>({kind:"Environmental",zone:x.zone_id,time:x.received_at}))
 ].filter(x=>valid(x.time));
 const domains=["Cybersecurity","Safety / PPE","Physical Security","Maintenance","Environmental"].map(name=>({name,value:sources.filter(x=>x.kind===name).length}));
 const decisions=[...incidents.filter(x=>valid(x.received_at)).map(x=>x.decision.severity),
  ...ssh.filter(x=>valid(x.received_at)).flatMap(x=>x.decision_record?[x.decision_record.decision.severity]:[]),
  ...operational.filter(x=>valid(x.maintenance.received_at)).flatMap(x=>x.decision_severity?[x.decision_severity]:[])];
 const received=new Map<string,string>([
  ...ssh.map(x=>["ssh:"+x.event_id,x.received_at] as [string,string]),
  ...ppe.map(x=>["ppe:"+x.observation_id,x.created_at] as [string,string]),
  ...face.map(x=>["face:"+x.observation_id,x.created_at] as [string,string])]);
 const candidateTime=(g:UnifiedCorrelationGroup)=>{const times=g.evidence.map(e=>Date.parse(received.get(e.kind+":"+e.observation_id)??"")).filter(Number.isFinite);return times.length?new Date(Math.max(...times)).toISOString():undefined};
 const severity=[{name:"HIGH",value:decisions.filter(x=>x==="HIGH").length},{name:"MEDIUM",value:decisions.filter(x=>x==="MEDIUM").length},{name:"LOW",value:decisions.filter(x=>x==="LOW").length}];
 const candidates=unified.filter(x=>x.domains.length>=3&&valid(candidateTime(x)));
 const combinations=new Map<string,number>();
 for(const group of candidates){const name=group.domains.join(" + ");combinations.set(name,(combinations.get(name)??0)+1)}
 const correlationBars=[...combinations].map(([name,value])=>({name,value}));
 const zoneCounts=new Map<string,number>();
 for(const item of sources)zoneCounts.set(item.zone,(zoneCounts.get(item.zone)??0)+1);
 const zones=[...zoneCounts].sort(([a],[b])=>a.localeCompare(b)).map(([name,value])=>({name,value}));
 const sourceTotal=domains.reduce((a,b)=>a+b.value,0);
 const daily=new Map<string,number>();
 for(const x of sources){const day=new Date(x.time).toLocaleDateString();daily.set(day,(daily.get(day)??0)+1)}
 const timeline=[...daily].sort((a,b)=>Date.parse(a[0])-Date.parse(b[0])).map(([name,value])=>({name,value}));
 return <section className="analyticsPage">
 <section className="panel analyticsFilterPanel" aria-label="Analytics time filters">
  <div className="analyticsFilterHeader"><div><h3>Reporting period</h3><p className="muted">Explore activity using Evidence receipt time.</p></div><span className="analyticsFilterMeta">READ-ONLY · LIVE DATA</span></div>
  <div className="analyticsRangeOptions" role="group" aria-label="Receipt time range">
   {([{value:"24h",label:"24 hours"},{value:"7d",label:"7 days"},{value:"30d",label:"30 days"},{value:"all",label:"All available"}] as const).map(option=><button key={option.value} type="button" className={range===option.value?"analyticsRangeOption selected":"analyticsRangeOption"} aria-pressed={range===option.value} onClick={()=>setRange(option.value)}>{option.label}</button>)}
  </div>
  <p className="muted analyticsFilterNote">Filters use receipt timestamps, not declared capture times. Authorized feed limits still apply.</p>
 </section>
 <div className="stats"><div className="panel"><small>Published source Evidence</small><strong>{sourceTotal}</strong></div><div className="panel"><small>Saved severity Decisions</small><strong>{decisions.length}</strong></div><div className="panel"><small>Unified candidates</small><strong>{candidates.length}</strong></div><div className="panel"><small>Observed zones</small><strong>{zones.length}</strong></div></div>
 <div className="analyticsGrid">
 <section className="panel"><h3>Evidence by domain</h3><p className="muted">Published source records; not incidents or Decisions.</p><Donut items={domains}/></section>
 <section className="panel"><h3>Saved Decision severity</h3><p className="muted">Only assigned standalone or operational Decision severities. Candidates and provisional reviews excluded.</p><Donut items={severity}/></section>
 <section className="panel"><h3>Multi-domain correlation candidates</h3><p className="muted">One count per unified group; pairwise links inside groups are not counted as separate incidents.</p>{correlationBars.length?<Bars items={correlationBars}/>:<p className="muted">No unified groups available.</p>}</section>
 <section className="panel"><h3>Evidence by zone</h3><p className="muted">Published source Evidence counts by declared zone.</p>{zones.length?<Bars items={zones}/>:<p className="muted">No source Evidence available.</p>}</section>
 <section className="panel"><h3>Evidence receipt activity</h3><p className="muted">Published Evidence by local receipt date.</p>{timeline.length?<Bars items={timeline}/>:<p className="muted">No Evidence received in this range.</p>}</section>
 </div>
 <p className="muted">Read-only analytics from authorized feed APIs, refreshed with Monitoring Center every five seconds. Feed limits and RBAC may affect totals. No inference of identity, causation or unified severity.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center</button>
 </section>;
}
