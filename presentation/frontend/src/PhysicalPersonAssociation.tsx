import {useEffect,useState} from "react";
import {getPhysicalPersonAssociation,type PhysicalPersonAssociation as Result} from "./api";
export default function PhysicalPersonAssociation({id}:{id:string}){
 const [result,setResult]=useState<Result|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{let active=true;setResult(null);setError(false);
 getPhysicalPersonAssociation(id).then(v=>{if(active)setResult(v)})
 .catch(()=>{if(active)setError(true)});
 return()=>{active=false}},[id]);
 return <section className="evidenceItem"><h4>Possible face-to-PPE person association</h4>
 {error?<p className="muted">Spatial association unavailable or access denied.</p>:
 !result?<p className="muted">Checking original detection geometry…</p>:
 <><p><b>{result.status.replaceAll("_"," ")}</b> · {result.reason.replaceAll("_"," ")}</p>
 {result.status==="MATCH_CANDIDATE"&&<p>Recognized face {result.recognized_person_id} may correspond to PPE Person {(result.person_index??0)+1}, assessed {result.ppe_status}. Face-box containment: {((result.face_containment_ratio??0)*100).toFixed(1)}%.</p>}
 <p className="muted">Geometric candidate only. Identity-to-PPE linkage is not verified. No Decision severity or autonomous action.</p></>}
 </section>;
}
