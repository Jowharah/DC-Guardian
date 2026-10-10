import {useEffect,useState} from "react";
import ImageCaptureDetails from "./ImageCaptureDetails";
import {getPPEImage,getPPEObservation,getEvidenceReview,type PPEObservationDetail,type EvidenceReviewEffective} from "./api";

export default function PPEObservationViewer({id}:{id:string}){
 const [detail,setDetail]=useState<PPEObservationDetail|null>(null);
 const [url,setUrl]=useState("");
 const [error,setError]=useState("");
 const [annotations,setAnnotations]=useState(true);
 const [human,setHuman]=useState<EvidenceReviewEffective|null>(null);
 useEffect(()=>{let active=true;setHuman(null);const load=()=>getEvidenceReview("ppe",id).then(r=>{if(active)setHuman(r.effective)}).catch(()=>{});void load();const timer=setInterval(load,5000);return()=>{active=false;clearInterval(timer)}},[id]);
 useEffect(()=>{
  let active=true;let objectUrl="";
  setDetail(null);setUrl("");setError("");
  Promise.all([getPPEObservation(id),getPPEImage(id)]).then(([d,blob])=>{
   if(!active)return;
   objectUrl=URL.createObjectURL(blob);setUrl(objectUrl);setDetail(d);
  }).catch(()=>{if(active)setError("Image evidence unavailable or access denied.")});
  return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)};
 },[id]);
 return <section className="panel ppeLab"><h3>Stored PPE image observation</h3><p className="muted">PPE-only model inference · not a pipeline incident · no Decision severity assigned.</p>
 {error?<p role="alert">{error}</p>:!detail||!url?<p>Loading authorized image…</p>:<>
  {human?.source==="HUMAN_OVERRIDE"?<p><b>{(human.effective_status??"").replaceAll("_"," ")} · human verified</b> by {human.reviewer} · detector reported {detail.status.replaceAll("_"," ")} · {detail.zone_id} · {new Date(detail.created_at).toLocaleString()}</p>:<p><b>{detail.status}</b> · {detail.zone_id} · {new Date(detail.created_at).toLocaleString()} · {human?(human.verdict==="CONFIRMED"?"human confirmed":"human review inconclusive"):detail.review_status}</p>}{human?.source==="HUMAN_OVERRIDE"&&<p className="muted">Boxes and per-person results below are the frozen detector output; the human verdict is recorded beside them, not written into them.</p>}
  <label><input type="checkbox" checked={annotations} onChange={e=>setAnnotations(e.target.checked)}/> Show YOLO annotations</label>
  <div className="ppePreview"><img src={url} alt="Stored original PPE observation"/>{annotations&&detail.assessment.detections.map((d,i)=>{
   const [x1,y1,x2,y2]=d.bbox_xyxy;return <div key={i} className="ppeBoundingBox" style={{left:`${x1/detail.image_size.width*100}%`,top:`${y1/detail.image_size.height*100}%`,width:`${(x2-x1)/detail.image_size.width*100}%`,height:`${(y2-y1)/detail.image_size.height*100}%`}} title={d.class_name}><span>{d.class_name} {(d.confidence*100).toFixed(0)}%</span></div>
  })}</div>
  <h4>Per-person PPE compliance</h4>
  <p className="muted">Frozen PPE-POLICY-v1 requires both helmet and safety vest for each detected person. A second person missing either item makes the overall image non-compliant.</p>
  {(detail.assessment.people??[]).map(person=><div className="evidenceItem" key={person.person_index}>
   <div className="incidentTop"><b>Detected person {person.person_index+1}</b><b>{person.status.replaceAll("_"," ")}</b></div>
   <p>Required PPE detected: {person.required_ppe_detected.length?person.required_ppe_detected.join(", "):"None"}</p>
   <p>Required PPE not associated: {person.required_ppe_not_detected.length?person.required_ppe_not_detected.join(", "):"None"}</p>
  </div>)}
  <ImageCaptureDetails kind="ppe" id={id}/><p className="muted">Original image is served through an authenticated API. Model detections are not independently verified by an operator.</p>
 </>}
 </section>;
}
