import InvestigatorMessage from "./InvestigatorMessage";
import {useEffect,useState} from "react";
import {type InvestigatorClaimCheck,askSingleEvidenceInvestigator,askPairInvestigator,type InvestigatorSingleKind,askOperationalInvestigator,askUnifiedInvestigator,getScopedInvestigatorHistory,saveScopedInvestigatorHistory,clearScopedInvestigatorHistory} from "./api";

type SourceRef={kind:string;id:string;role:string};
type FieldCheck={status:string;summary?:{matched:number;mismatched:number;source_unavailable:number;recognized:number};checks:{field:string;claim:string;source_value:number|string|string[]|null;status:string;domain?:string;evidence_id?:string|null}[];skipped?:{domain:string;reason:string;count:number}[];note:string};
type GroundingCheck={status:string;referenced_ids:string[];unrecognized_ids:string[];claim_validation:string;note:string};
type Message={role:"operator"|"investigator";text:string;sources?:SourceRef[];grounding?:GroundingCheck;fieldGrounding?:FieldCheck;claimChecks?:InvestigatorClaimCheck};
export default function InvestigatorPanel({groupId,investigationType="unified",singleKind,workspace,expanded,onToggleExpanded}:{groupId:string|null;investigationType?:"unified"|"pairs"|"operations"|"single";singleKind?:InvestigatorSingleKind;workspace:string;expanded:boolean;onToggleExpanded:()=>void}){
 const [question,setQuestion]=useState("");
 const [consent,setConsent]=useState(false);
 const [messages,setMessages]=useState<Message[]>([]);
 const [busy,setBusy]=useState(false);
 const [saveChats,setSaveChats]=useState(false);
 const [historyAvailable,setHistoryAvailable]=useState(false);
 const [historyNote,setHistoryNote]=useState("");
 const [error,setError]=useState("");
 useEffect(()=>{
  let active=true;
  setMessages([]);setQuestion("");setConsent(false);setSaveChats(false);setHistoryAvailable(false);setHistoryNote("");setError("");
  if(groupId)getScopedInvestigatorHistory(investigationType,groupId,singleKind).then(result=>{
   if(!active)return;
   setHistoryAvailable(true);
   setMessages(result.messages.flatMap(item=>[{role:"operator" as const,text:item.question},{role:"investigator" as const,text:item.answer}]));
  }).catch(()=>{if(active)setHistoryNote("Conversation history is disabled or unavailable. Messages will remain in this tab only.")});
  return()=>{active=false};
 },[groupId,investigationType,singleKind]);
 async function send(){
  const value=question.trim();
  if(!groupId||!consent||value.length<3||busy)return;
  setBusy(true);setError("");
  try{
   const result=investigationType==="single"&&singleKind?await askSingleEvidenceInvestigator(singleKind,groupId,value):investigationType==="pairs"?await askPairInvestigator(groupId,value):investigationType==="operations"?await askOperationalInvestigator(groupId,value):await askUnifiedInvestigator(groupId,value);
   setMessages(previous=>[...previous,{role:"operator",text:value},{role:"investigator",text:result.answer,sources:"sources" in result?result.sources:undefined,grounding:"grounding_check" in result?result.grounding_check:undefined,fieldGrounding:"field_grounding" in result?result.field_grounding??undefined:undefined,claimChecks:"claim_checks" in result?result.claim_checks:undefined}]);
   if(saveChats&&historyAvailable&&groupId){
    try{await saveScopedInvestigatorHistory(investigationType,groupId,value,result.answer,singleKind)}
    catch{setHistoryNote("Answer received, but conversation history could not be saved.")}
   }
   setQuestion("");
  }catch(e){setError(e instanceof Error?e.message:"Investigator unavailable")}
  finally{setBusy(false)}
 }
 return <aside className={`agentSidebar ${expanded?"agentSidebarExpanded":""}`} aria-label="AI Investigator">
  <div className="agentHeading"><div className="agentAvatar">✦</div><div className="agentHeadingText"><b>AI Investigator</b><small>OpenAI · read-only · opt-in</small></div><button type="button" className="investigatorExpandButton" onClick={onToggleExpanded} aria-label={expanded?"Collapse AI Investigator":"Expand AI Investigator"} aria-expanded={expanded} title={expanded?"Return to sidebar view":"Expand chat workspace"}><span aria-hidden="true">{expanded?"↘":"⤢"}</span><span>{expanded?"Collapse":"Expand"}</span></button></div>
  <div className="agentContext"><small>WORKSPACE CONTEXT</small><b>{workspace}</b>
   <p>{groupId?"Selected "+(investigationType==="pairs"?"correlation pair":investigationType==="operations"?"operational correlation":investigationType==="single"?"single "+(singleKind??"")+" Evidence":"unified investigation")+": "+groupId:"Select an Evidence event or correlation in Monitoring Center to ask questions."}</p></div>
  <div className="agentConversation" aria-live="polite">
   {messages.length===0?<div className="agentMessage">Ask about existing saved detector assessments, contextual correlations, deterministic review, or recorded human outcomes. No new model inference or Decision is created.</div>:
    messages.map((m,i)=><div key={i} className={`agentMessage investigatorChatBubble ${m.role==="operator"?"investigatorOperatorBubble":"investigatorAssistantBubble"}`}><div className="investigatorSpeaker"><span className="investigatorSpeakerIcon" aria-hidden="true">{m.role==="operator"?"●":"✦"}</span><b>{m.role==="operator"?"You":"AI Investigator"}</b></div>{m.role==="operator"?<p>{m.text}</p>:<><InvestigatorMessage text={m.text}/>{m.claimChecks&&<details className="investigatorSources" open={m.claimChecks.status==="VIOLATION"||m.claimChecks.status==="MISMATCH"}><summary>Claim checks · {m.claimChecks.status.replaceAll("_"," ")}{m.claimChecks.summary.violations+m.claimChecks.summary.state_mismatches>0?` · ⚠ ${m.claimChecks.summary.violations} boundary violation(s), ${m.claimChecks.summary.state_mismatches} state mismatch(es)`:""}</summary>{m.claimChecks.model_judge&&m.claimChecks.model_judge.status!=="DISABLED"&&<div className="judgeFindings"><p><strong>Model check:</strong> {m.claimChecks.model_judge.status==="FLAGGED"?"these sentences state more than the Evidence establishes":m.claimChecks.model_judge.status==="CLEAN"?"no presence, cause or PPE-absence claims found":"unavailable for this answer (it was not checked)"}.</p>{m.claimChecks.model_judge.findings.length>0&&<ul>{m.claimChecks.model_judge.findings.map((f,j)=><li key={j}><strong>{f.type==="PRESENCE"?"Presence":f.type==="CAUSATION"?"Cause":"PPE absence"}</strong> · “{f.sentence}” · {f.reason}</li>)}</ul>}<p className="muted">Measured on labelled answers it catches most such claims (4 of 5 on unseen answers) with few false alarms; a clean result is not verification.</p></div>}<p>{m.claimChecks.note}</p>{m.claimChecks.checks.length>0?<ul>{m.claimChecks.checks.map((c,j)=><li key={j}><strong>{c.status}</strong> · {c.type==="BOUNDARY"?(c.boundary??"").replaceAll("_"," ").toLowerCase()+" claim":`${(c.domain??"").toUpperCase()} state "${(c.claimed??"").replaceAll("_"," ")}" vs detector ${(c.detector_state??"n/a").replaceAll("_"," ")}${c.human_status?`, human ${c.human_status.replaceAll("_"," ")}`:""}`} · “{c.sentence}”</li>)}</ul>:<p>No recognized boundary or state claims.</p>}{m.claimChecks.skipped.length>0&&<p>Skipped: {m.claimChecks.skipped.map(s=>s.domain+" ("+s.reason.replaceAll("_"," ").toLowerCase()+")").join(", ")}</p>}</details>}{m.fieldGrounding&&<details className="investigatorSources"><summary>Numeric &amp; identity field checks ({m.fieldGrounding.checks.length}){m.fieldGrounding.summary&&m.fieldGrounding.summary.mismatched>0?" · ⚠ "+m.fieldGrounding.summary.mismatched+" mismatched":""}</summary>{m.fieldGrounding.summary&&<p><strong>{m.fieldGrounding.summary.matched} matched</strong> against saved detector output · {m.fieldGrounding.summary.mismatched} mismatched · {m.fieldGrounding.summary.source_unavailable} source fields unavailable.</p>}<p>{m.fieldGrounding.note}</p><p>Other narrative (beyond the claim checks): not verified. Source authenticity: not independently verified.</p>{m.fieldGrounding.checks.length>0?<ul>{m.fieldGrounding.checks.map((check,j)=><li key={j}>{check.domain&&<>{check.domain.toUpperCase()} · </>}<strong>{check.field}</strong> · {check.status} · Claimed: {check.claim} · Saved value: {check.source_value===null||check.source_value===undefined?"Unavailable":Array.isArray(check.source_value)?(check.source_value.join(", ")||"none"):String(check.source_value)}</li>)}</ul>:<p>No supported numerical phrasing was recognized.</p>}{m.fieldGrounding.skipped&&m.fieldGrounding.skipped.length>0&&<p className="muted">Not checked: {m.fieldGrounding.skipped.map(s=>`${s.domain} (${s.count} members; a number cannot be attributed to one without guessing)`).join("; ")}.</p>}</details>}{m.grounding&&<div className="investigatorGrounding" role="status"><div className="investigatorGroundingTitle"><span aria-hidden="true">◇</span><strong>Evidence grounding</strong></div><div><span>Reference check</span><b className={m.grounding.status==="UNVERIFIED_REFERENCES"?"investigatorGroundingWarning":"investigatorGroundingNeutral"}>{m.grounding.status==="UNVERIFIED_REFERENCES"?"Unrecognized Evidence IDs":"Reference check only"}</b></div><div><span>Claim-level verification</span><b>Not performed</b></div>{m.grounding.unrecognized_ids.length>0&&<p>Unrecognized references: {m.grounding.unrecognized_ids.join(", ")}</p>}<small>Matching an Evidence ID does not validate the AI's factual claims.</small></div>}{m.sources&&m.sources.length>0&&<details className="investigatorSources"><summary>Source Evidence ({m.sources.length})</summary><p>Authorized source references only. Individual AI claims have not been independently verified.</p><ul>{m.sources.map((source,j)=><li key={j}><strong>{source.kind}</strong> · <code>{source.id}</code></li>)}</ul></details>}</>}</div>)}
   {error&&<p role="alert" className="error">{error.includes("INVESTIGATOR_NOT_ENABLED")||error.includes("(503)")?"The Investigator backend is not enabled or the OpenAI provider is unavailable. Ask your administrator to check the server configuration.":error}</p>}
  </div>
  {groupId&&<div className="investigatorHistoryControls">
   <label className="investigatorConsent"><input type="checkbox" checked={saveChats} disabled={!historyAvailable||busy} onChange={e=>setSaveChats(e.target.checked)}/> Save new conversations privately for this investigation (local test storage).</label>
   <button type="button" disabled={!historyAvailable||busy} onClick={async()=>{if(!groupId||!window.confirm("Delete your saved Investigator conversation for this investigation?"))return;try{await clearScopedInvestigatorHistory(investigationType,groupId,singleKind);setMessages([]);setHistoryNote("Saved conversation cleared.")}catch{setHistoryNote("Could not clear saved conversation.")}}}>Clear saved chat</button>
   {historyNote&&<small role="status">{historyNote}</small>}
  </div>}
  <div className="agentComposer">
   <label className="investigatorConsent"><input type="checkbox" checked={consent} disabled={!groupId||busy} onChange={e=>setConsent(e.target.checked)}/> I authorize sending the selected investigation's filtered Evidence context and my question to OpenAI for this request.</label>
   <textarea aria-label="Ask AI Investigator" value={question} disabled={!groupId||busy} maxLength={1000} placeholder={groupId?"Ask about this investigation…":"Select a unified investigation first"} onChange={e=>setQuestion(e.target.value)}/>
   <button type="button" disabled={!groupId||!consent||question.trim().length<3||busy} onClick={()=>void send()}>{busy?"Analyzing…":"Send"}</button>
   <small>Read-only explanation · No severity assignment · No autonomous action</small>
  </div>
 </aside>;
}
