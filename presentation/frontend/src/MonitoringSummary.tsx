import {useEffect,useState} from "react";
import {apiHealth,getUnifiedSpecialists,type Incident,type OperationalCorrelation,type PublishedSSH,type UnifiedCorrelationGroup} from "./api";
import {DOMAINS,type Domain,type OutcomeRecord} from "./detectorOutcomes";

export type Focus="attention"|"abnormal"|"correlations"|"decisions"|`domain:${Domain}`;
export const focusLabel=(focus:Focus)=>focus.startsWith("domain:")?focus.slice(7)+" Evidence and correlations":
 {attention:"Items needing attention",abnormal:"Abnormal detector results and the correlations that contain them",
  correlations:"Correlation groups and pairs",decisions:"Saved severity Decisions"}[focus as Exclude<Focus,`domain:${Domain}`>];

const DAY=86400000;
const ago=(ms:number)=>ms<60000?`${Math.max(0,Math.round(ms/1000))} s ago`:ms<3600000?`${Math.round(ms/60000)} min ago`:ms<DAY?`${Math.round(ms/3600000)} h ago`:`${Math.round(ms/DAY)} d ago`;

/** Unified groups without a current saved specialist evaluation (404 none saved, 409 Evidence changed since). */
export function useUnevaluatedGroups(ids:string[]){
 const [unevaluated,setUnevaluated]=useState<Set<string>>(new Set());
 const key=[...ids].sort().join("|");
 useEffect(()=>{
  let active=true;
  const list=key?key.split("|"):[];
  const refresh=async()=>{
   const results=await Promise.all(list.map(id=>getUnifiedSpecialists(id).then(()=>null).catch((e:unknown)=>
    e instanceof Error&&(e.message.includes("(404)")||e.message.includes("(409)"))?id:null)));
   if(active)setUnevaluated(new Set(results.filter((x):x is string=>x!==null)));
  };
  void refresh();
  const timer=setInterval(()=>void refresh(),10000);
  return()=>{active=false;clearInterval(timer)};
 },[key]);
 return unevaluated;
}

/** Live/delayed/offline from the time of the last API answer, so stale numbers are visible as stale. */
export function LiveStatus(){
 const [now,setNow]=useState(Date.now());
 useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer)},[]);
 const since=apiHealth.lastContact?now-apiHealth.lastContact:Infinity;
 const state=since<12000?"live":since<60000?"delayed":"offline";
 const text=state==="live"?`Live · updated ${ago(since)}`:state==="delayed"?`Delayed · last update ${ago(since)}`:
  apiHealth.lastContact?`Offline · last update ${ago(since)}`:"Connecting…";
 return <span className={`liveStatus live-${state}`} role="status" title="Time since the dashboard last received an answer from the API (refresh every 5 seconds)"><span className="liveDot"/>{text}</span>;
}

type Props={records:OutcomeRecord[];incidents:Incident[];ssh:PublishedSSH[];operational:OperationalCorrelation[];
 unified:UnifiedCorrelationGroup[];pairCount:number;unevaluated:Set<string>;
 focus:Focus|null;setFocus:(focus:Focus|null)=>void;openReview:()=>void};

export default function MonitoringSummary({records,incidents,ssh,operational,unified,pairCount,unevaluated,focus,setFocus,openReview}:Props){
 const now=Date.now();
 const toReview=records.filter(r=>r.abnormal&&!r.verdict).length;
 const reevaluate=ssh.filter(x=>x.decision_record?.input_review?.reevaluation_required).length+
  operational.filter(x=>x.input_review?.reevaluation_required).length;
 const notEvaluated=unified.filter(g=>unevaluated.has(g.id)).length;
 const attention=toReview+notEvaluated+reevaluate;
 const abnormal=records.filter(r=>r.abnormal);
 const recentAbnormal=abnormal.filter(r=>now-Date.parse(r.time)<DAY).length;
 const severities=[...incidents.map(x=>x.decision.severity),
  ...ssh.flatMap(x=>x.decision_record?.decision.severity?[x.decision_record.decision.severity]:[]),
  ...operational.flatMap(x=>x.decision_severity?[x.decision_severity]:[])];
 const count=(level:string)=>severities.filter(x=>x===level).length;
 const toggle=(next:Focus)=>setFocus(focus===next?null:next);
 const card=(id:Focus,title:string,value:string|number,detail:React.ReactNode,tone="")=>
  <button type="button" className={`panel summaryCard ${tone} ${focus===id?"selected":""}`} aria-pressed={focus===id} onClick={()=>toggle(id)}>
   <small>{title}</small><strong>{value}</strong><span className="summaryDetail">{detail}</span></button>;
 return <section aria-label="Monitoring summary">
  <div className="stats summaryCards">
   {card("attention","Needs attention",attention,[toReview?`${toReview} abnormal without verdict`:"",notEvaluated?`${notEvaluated} group${notEvaluated===1?"":"s"} not evaluated`:"",reevaluate?`${reevaluate} Decision${reevaluate===1?"":"s"} to re-evaluate`:""].filter(Boolean).join(" · ")||"Nothing outstanding",attention?"summaryAlert":"")}
   {card("abnormal","Abnormal detector results",`${abnormal.length} of ${records.length}`,<>{recentAbnormal} in the last 24 h · display only, not severity</>)}
   {card("correlations","Correlations",`${unified.length} group${unified.length===1?"":"s"}`,<>{pairCount} pair{pairCount===1?"":"s"} · {notEvaluated} group{notEvaluated===1?"":"s"} awaiting specialists</>)}
   {card("decisions","Saved Decisions",severities.length,<><span className="severity severity-high">HIGH {count("HIGH")}</span> <span className="severity severity-medium">MED {count("MEDIUM")}</span> <span className="severity severity-low">LOW {count("LOW")}</span>{reevaluate?<> · ⚠ {reevaluate} re-evaluate</>:null}</>)}
  </div>
  <div className="domainStrip" role="group" aria-label="Domain status">
   {DOMAINS.map(domain=>{
    const items=records.filter(r=>r.domain===domain);
    const latest=Math.max(...items.map(r=>Date.parse(r.time)).filter(Number.isFinite),-Infinity);
    const age=Number.isFinite(latest)?now-latest:Infinity;
    const fresh=age<3600000?"fresh":age<DAY?"recent":"stale";
    const id=`domain:${domain}` as Focus;
    return <button type="button" key={domain} className={`domainChip ${focus===id?"selected":""}`} aria-pressed={focus===id} onClick={()=>toggle(id)}
      title={Number.isFinite(age)?`Last Evidence received ${ago(age)}`:"No Evidence received"}>
     <span className={`freshDot fresh-${fresh}`}/><b>{domain}</b> {items.filter(r=>r.abnormal).length}/{items.length}
     <small>{Number.isFinite(age)?ago(age):"no data"}</small></button>;
   })}
   <span className="muted domainStripNote">abnormal / total · last received</span>
  </div>
  {attention>0&&focus==="attention"&&<p className="muted">Human verdicts and group reviews are recorded in the <button type="button" className="linkButton" onClick={openReview}>Human Review Queue</button>.</p>}
 </section>;
}
