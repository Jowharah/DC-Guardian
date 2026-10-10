import InvestigatorMessage from "./InvestigatorMessage";
import {useEffect,useState} from "react";
import {askUnifiedInvestigator,getInvestigatorHistory,saveInvestigatorHistory,clearInvestigatorHistory} from "./api";

type Message={role:"operator"|"investigator";text:string};
export default function InvestigatorPanel({groupId,workspace,expanded,onToggleExpanded}:{groupId:string|null;workspace:string;expanded:boolean;onToggleExpanded:()=>void}){
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
  if(groupId)getInvestigatorHistory(groupId).then(result=>{
   if(!active)return;
   setHistoryAvailable(true);
   setMessages(result.messages.flatMap(item=>[{role:"operator" as const,text:item.question},{role:"investigator" as const,text:item.answer}]));
  }).catch(()=>{if(active)setHistoryNote("Conversation history is disabled or unavailable. Messages will remain in this tab only.")});
  return()=>{active=false};
 },[groupId]);
 async function send(){
  const value=question.trim();
  if(!groupId||!consent||value.length<3||busy)return;
  setBusy(true);setError("");
  try{
   const result=await askUnifiedInvestigator(groupId,value);
   setMessages(previous=>[...previous,{role:"operator",text:value},{role:"investigator",text:result.answer}]);
   if(saveChats&&historyAvailable&&groupId){
    try{await saveInvestigatorHistory(groupId,value,result.answer)}
    catch{setHistoryNote("Answer received, but conversation history could not be saved.")}
   }
   setQuestion("");
  }catch(e){setError(e instanceof Error?e.message:"Investigator unavailable")}
  finally{setBusy(false)}
 }
 return <aside className={`agentSidebar ${expanded?"agentSidebarExpanded":""}`} aria-label="AI Investigator">
  <div className="agentHeading"><div className="agentAvatar">✦</div><div className="agentHeadingText"><b>AI Investigator</b><small>OpenAI · read-only · opt-in</small></div><button type="button" className="investigatorExpandButton" onClick={onToggleExpanded} aria-label={expanded?"Collapse AI Investigator":"Expand AI Investigator"} aria-expanded={expanded} title={expanded?"Return to sidebar view":"Expand chat workspace"}><span aria-hidden="true">{expanded?"↘":"⤢"}</span><span>{expanded?"Collapse":"Expand"}</span></button></div>
  <div className="agentContext"><small>WORKSPACE CONTEXT</small><b>{workspace}</b>
   <p>{groupId?"Selected unified investigation: "+groupId:"Open a unified investigation in Monitoring Center to ask Evidence questions."}</p></div>
  <div className="agentConversation" aria-live="polite">
   {messages.length===0?<div className="agentMessage">Ask about existing saved detector assessments, contextual correlations, deterministic review, or recorded human outcomes. No new model inference or Decision is created.</div>:
    messages.map((m,i)=><div key={i} className={`agentMessage investigatorChatBubble ${m.role==="operator"?"investigatorOperatorBubble":"investigatorAssistantBubble"}`}><div className="investigatorSpeaker"><span className="investigatorSpeakerIcon" aria-hidden="true">{m.role==="operator"?"●":"✦"}</span><b>{m.role==="operator"?"You":"AI Investigator"}</b></div>{m.role==="operator"?<p>{m.text}</p>:<InvestigatorMessage text={m.text}/>}</div>)}
   {error&&<p role="alert" className="error">{error.includes("INVESTIGATOR_NOT_ENABLED")||error.includes("(503)")?"The Investigator backend is not enabled or the OpenAI provider is unavailable. Ask your administrator to check the server configuration.":error}</p>}
  </div>
  {groupId&&<div className="investigatorHistoryControls">
   <label className="investigatorConsent"><input type="checkbox" checked={saveChats} disabled={!historyAvailable||busy} onChange={e=>setSaveChats(e.target.checked)}/> Save new conversations privately for this investigation (local test storage).</label>
   <button type="button" disabled={!historyAvailable||busy} onClick={async()=>{if(!groupId||!window.confirm("Delete your saved Investigator conversation for this investigation?"))return;try{await clearInvestigatorHistory(groupId);setMessages([]);setHistoryNote("Saved conversation cleared.")}catch{setHistoryNote("Could not clear saved conversation.")}}}>Clear saved chat</button>
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
