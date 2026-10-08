import {useEffect,useState} from "react";
import {getPPEObservations,type PPEObservation} from "./api";
import PPEObservationViewer from "./PPEObservationViewer";
export default function PPEObservationFeed(){
 const [items,setItems]=useState<PPEObservation[]>([]);
 const [selected,setSelected]=useState<string|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{let active=true;const refresh=()=>getPPEObservations().then(v=>{if(active)setItems(v)}).catch(()=>{if(active)setError("PPE observations unavailable for this role or zone.")});refresh();const timer=setInterval(refresh,5000);return()=>{active=false;clearInterval(timer)}},[]);
 return <section><h2>PPE image observations</h2><p className="muted">Separate from pipeline incidents · operator-uploaded image validations · no Decision severity.</p>{error?<p className="muted">{error}</p>:<div className="panel feed">{items.length===0?<p className="muted">No retained PPE image observations.</p>:items.map(item=><button key={item.observation_id} className={`feedRow incidentButton ${selected===item.observation_id?"selected":""}`} onClick={()=>setSelected(v=>v===item.observation_id?null:item.observation_id)} aria-expanded={selected===item.observation_id}><span>{new Date(item.created_at).toLocaleString()}</span><span><b>{item.observation_id}</b><small>PPE IMAGE VALIDATION · {item.review_status}</small></span><span>{item.zone_id}</span><span>{item.status}</span></button>)}</div>}{selected&&<PPEObservationViewer id={selected}/>}</section>;
}
