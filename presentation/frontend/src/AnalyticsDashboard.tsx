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
 const domains=[{name:"Cybersecurity",value:ssh.length},{name:"Safety / PPE",value:ppe.length},{name:"Physical Security",value:face.length},{name:"Maintenance",value:maintenance.length},{name:"Environmental",value:environment.length}];
 const decisions=[...incidents.map(x=>x.decision.severity),...ssh.flatMap(x=>x.decision_record?[x.decision_record.decision.severity]:[]),...operational.flatMap(x=>x.decision_severity?[x.decision_severity]:[])];
 const severity=[{name:"HIGH",value:decisions.filter(x=>x==="HIGH").length},{name:"MEDIUM",value:decisions.filter(x=>x==="MEDIUM").length},{name:"LOW",value:decisions.filter(x=>x==="LOW").length}];
 const candidates=unified.filter(x=>x.domains.length>=3);
 const combinations=new Map<string,number>();
 for(const group of candidates){const name=group.domains.join(" + ");combinations.set(name,(combinations.get(name)??0)+1)}
 const correlationBars=[...combinations].map(([name,value])=>({name,value}));
 const zoneCounts=new Map<string,number>();
 for(const item of [...ssh,...ppe,...face,...maintenance,...environment])zoneCounts.set(item.zone_id,(zoneCounts.get(item.zone_id)??0)+1);
 const zones=[...zoneCounts].sort(([a],[b])=>a.localeCompare(b)).map(([name,value])=>({name,value}));
 const sourceTotal=domains.reduce((a,b)=>a+b.value,0);
 return <section className="analyticsPage">
 <div className="stats"><div className="panel"><small>Published source Evidence</small><strong>{sourceTotal}</strong></div><div className="panel"><small>Saved severity Decisions</small><strong>{decisions.length}</strong></div><div className="panel"><small>Unified candidates</small><strong>{candidates.length}</strong></div><div className="panel"><small>Observed zones</small><strong>{zones.length}</strong></div></div>
 <div className="analyticsGrid">
 <section className="panel"><h3>Evidence by domain</h3><p className="muted">Published source records; not incidents or Decisions.</p><Donut items={domains}/></section>
 <section className="panel"><h3>Saved Decision severity</h3><p className="muted">Only assigned standalone or operational Decision severities. Candidates and provisional reviews excluded.</p><Donut items={severity}/></section>
 <section className="panel"><h3>Multi-domain correlation candidates</h3><p className="muted">One count per unified group; pairwise links inside groups are not counted as separate incidents.</p>{correlationBars.length?<Bars items={correlationBars}/>:<p className="muted">No unified groups available.</p>}</section>
 <section className="panel"><h3>Evidence by zone</h3><p className="muted">Published source Evidence counts by declared zone.</p>{zones.length?<Bars items={zones}/>:<p className="muted">No source Evidence available.</p>}</section>
 </div>
 <p className="muted">Read-only analytics from authorized feed APIs, refreshed with Monitoring Center every five seconds. Feed limits and RBAC may affect totals. No inference of identity, causation or unified severity.</p>
 <button type="button" onClick={openMonitoring}>Open Monitoring Center</button>
 </section>;
}
