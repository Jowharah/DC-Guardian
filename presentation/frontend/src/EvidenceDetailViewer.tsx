import {useState} from "react";
import {getEvidenceDetail,type EvidenceEvent,type EvidenceDetail} from "./api";

function ValueView({value}:{value:unknown}):React.ReactNode{
 if(value===null||value===undefined)return "Not provided";
 if(Array.isArray(value))return <ul>{value.map((item,i)=><li key={i}><ValueView value={item}/></li>)}</ul>;
 if(typeof value==="object")return <dl>{Object.entries(value as Record<string,unknown>).map(([key,item])=><div key={key}><dt>{key.replaceAll("_"," ")}</dt><dd><ValueView value={item}/></dd></div>)}</dl>;
 return String(value);
}
export default function EvidenceDetailViewer({scenarioId,event}:{scenarioId:string;event:EvidenceEvent}){
 const [open,setOpen]=useState(false);
 const [detail,setDetail]=useState<EvidenceDetail|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(false);
 async function toggle(){
  if(open){setOpen(false);return}
  setOpen(true);setLoading(true);setError("");
  try{setDetail(await getEvidenceDetail(scenarioId,event.event_id))}
  catch(e){setError(e instanceof Error?e.message:"Unable to retrieve evidence")}
  finally{setLoading(false)}
 }
 return <div className="evidenceDetail"><button type="button" className="closeIncident" onClick={()=>void toggle()} aria-expanded={open}>{open?"Hide source details":"Inspect source details"}</button>
 {open&&<div className="evidenceItem">{loading?<p>Loading authorized evidence…</p>:error?<p role="status">{error==="API request failed (403)"?"Access restricted for your role or zone.":error==="API request failed (404)"?"Detailed Evidence unavailable for this incident. Run a new controlled scenario.":error}</p>:detail?<><p className="muted">{detail.availability.replaceAll("_"," ")} · {detail.source_type}</p>{Object.entries(detail.details).map(([group,value])=><div key={group}><h5>{group.replaceAll("_"," ")}</h5><ValueView value={value}/></div>)}</>:null}</div>}
 </div>;
}
