import {useEffect,useState} from "react";
import {getPPEImage,getPPEObservation,type PPEObservationDetail} from "./api";

export default function PPEObservationViewer({id}:{id:string}){
 const [detail,setDetail]=useState<PPEObservationDetail|null>(null);
 const [url,setUrl]=useState("");
 const [error,setError]=useState("");
 const [annotations,setAnnotations]=useState(true);
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
  <p><b>{detail.status}</b> · {detail.zone_id} · {new Date(detail.created_at).toLocaleString()} · {detail.review_status}</p>
  <label><input type="checkbox" checked={annotations} onChange={e=>setAnnotations(e.target.checked)}/> Show YOLO annotations</label>
  <div className="ppePreview"><img src={url} alt="Stored original PPE observation"/>{annotations&&detail.assessment.detections.map((d,i)=>{
   const [x1,y1,x2,y2]=d.bbox_xyxy;return <div key={i} className="ppeBoundingBox" style={{left:`${x1/detail.image_size.width*100}%`,top:`${y1/detail.image_size.height*100}%`,width:`${(x2-x1)/detail.image_size.width*100}%`,height:`${(y2-y1)/detail.image_size.height*100}%`}} title={d.class_name}><span>{d.class_name} {(d.confidence*100).toFixed(0)}%</span></div>
  })}</div>
  <p className="muted">Original image is served through an authenticated API. Model detections are not independently verified by an operator.</p>
 </>}
 </section>;
}
