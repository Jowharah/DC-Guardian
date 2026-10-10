import InvestigatorMessage from "./InvestigatorMessage";
import {useEffect,useState} from "react";
import {askUnifiedInvestigator} from "./api";

type Message={role:"operator"|"investigator";text:string};
export default function InvestigatorPanel({groupId,workspace}:{groupId:string|null;workspace:string}){
 const [question,setQuestion]=useState("");
 const [consent,setConsent]=useState(false);
 const [messages,setMessages]=useState<Message[]>([]);
 const [busy,setBusy]=useState(false);
 const [error,setError]=useState("");
 useEffect(()=>{setMessages([]);setQuestion("");setConsent(false);setError("")},[groupId]);
 async function send(){
  const value=question.trim();
  if(!groupId||!consent||value.length<3||busy)return;
  setBusy(true);setError("");
  try{
   const result=await askUnifiedInvestigator(groupId,value);
   setMessages(previous=>[...previous,{role:"operator",text:value},{role:"investigator",text:result.answer}]);
   setQuestion("");
  }catch(e){setError(e instanceof Error?e.message:"Investigator unavailable")}
  finally{setBusy(false)}
 }
 return <aside className="agentSidebar">
  <div className="agentHeading"><div className="agentAvatar">✦</div><div><b>AI Investigator</b><small>OpenAI · read-only · opt-in</small></div></div>
  <div className="agentContext"><small>WORKSPACE CONTEXT</small><b>{workspace}</b>
   <p>{groupId?"Selected unified investigation: "+groupId:"Open a unified investigation in Monitoring Center to ask Evidence questions."}</p></div>
  <div className="agentConversation" aria-live="polite">
   {messages.length===0?<div className="agentMessage">Ask about existing saved detector assessments, contextual correlations, deterministic review, or recorded human outcomes. No new model inference or Decision is created.</div>:
    messages.map((m,i)=><div key={i} className={`agentMessage investigatorChatBubble ${m.role==="operator"?"investigatorOperatorBubble":"investigatorAssistantBubble"}`}><div className="investigatorSpeaker"><span className="investigatorSpeakerIcon" aria-hidden="true">{m.role==="operator"?"●":"✦"}</span><b>{m.role==="operator"?"You":"AI Investigator"}</b></div>{m.role==="operator"?<p>{m.text}</p>:<InvestigatorMessage text={m.text}/>}</div>)}
   {error&&<p role="alert" className="error">{error.includes("INVESTIGATOR_NOT_ENABLED")||error.includes("(503)")?"The Investigator backend is not enabled or the OpenAI provider is unavailable. Ask your administrator to check the server configuration.":error}</p>}
  </div>
  <div className="agentComposer">
   <label className="investigatorConsent"><input type="checkbox" checked={consent} disabled={!groupId||busy} onChange={e=>setConsent(e.target.checked)}/> I authorize sending the selected investigation's filtered Evidence context and my question to OpenAI for this request.</label>
   <textarea aria-label="Ask AI Investigator" value={question} disabled={!groupId||busy} maxLength={1000} placeholder={groupId?"Ask about this investigation…":"Select a unified investigation first"} onChange={e=>setQuestion(e.target.value)}/>
   <button type="button" disabled={!groupId||!consent||question.trim().length<3||busy} onClick={()=>void send()}>{busy?"Analyzing…":"Send"}</button>
   <small>Read-only explanation · No severity assignment · No autonomous action</small>
  </div>
 </aside>;
}
