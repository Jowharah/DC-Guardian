import {useEffect,useState} from "react";
import {validatePPEImage,type PPEImageResult} from "./api";

export default function PPEImageLab(){
 const [file,setFile]=useState<File|null>(null);
 const [preview,setPreview]=useState("");
 const [result,setResult]=useState<PPEImageResult|null>(null);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 const [retain,setRetain]=useState(false);
 const [zone,setZone]=useState("ZONE-B");
 useEffect(()=>{if(!file){setPreview("");return}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url)},[file]);
 async function run(){
  if(!file)return;setBusy(true);setError("");setResult(null);
  try{setResult(await validatePPEImage(file,retain,zone))}
  catch(e){const message=e instanceof Error?e.message:"Upload failed";setError(message.includes("503")?"PPE inference could not run. The backend will report whether CUDA or the frozen model artifacts are unavailable. No prediction was generated.":message)}
  finally{setBusy(false)}
 }
 return <section className="panel ppeLab"><h3>PPE image validation</h3><p className="muted">Upload a licensed test image or approved snapshot. Runs the frozen PPE detector when CUDA is available. This does not create an incident or perform face identification.</p>
  <label className="ppeFileLabel">JPEG or PNG (maximum 8 MiB)<input type="file" accept="image/png,image/jpeg" onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null);setError("")}}/></label>
  {preview&&<div className="ppePreview"><img src={preview} alt="Selected PPE validation image"/>{result?.assessment.detections?.map((d,i)=>{const [x1,y1,x2,y2]=d.bbox_xyxy;const w=result.image_size.width,h=result.image_size.height;return <div key={i} className="ppeBoundingBox" style={{left:`${x1/w*100}%`,top:`${y1/h*100}%`,width:`${(x2-x1)/w*100}%`,height:`${(y2-y1)/h*100}%`}} title={`${d.class_name} ${(d.confidence*100).toFixed(1)}%`}><span>{d.class_name} {(d.confidence*100).toFixed(0)}%</span></div>})}</div>}
  <label><input type="checkbox" checked={retain} onChange={e=>setRetain(e.target.checked)}/> Retain this image as a local PPE observation for investigation (use test/approved images only)</label>
  {retain&&<label>Assigned zone <select value={zone} onChange={e=>setZone(e.target.value)}><option value="ZONE-A">ZONE-A</option><option value="ZONE-B">ZONE-B</option><option value="ZONE-C">ZONE-C</option></select></label>}
  <button type="button" disabled={!file||busy} onClick={()=>void run()}>{busy?"Running frozen model…":"Validate PPE image"}</button>
  {error&&<p role="alert" className="error">{error}</p>}
  {result&&<div className="evidenceItem"><h4>Model assessment: {result.assessment.overall_status}</h4><p>People detected: {result.assessment.person_count} · Detections: {result.assessment.detections?.length??0}</p><p className="muted">{result.image_stored?"Image retained in protected local Evidence storage. Open Monitoring Center to review it.":"Image is shown only in this browser; it was not saved."} This is PPE-only inference, not a complete DC-GUARDIAN incident.</p>{result.assessment.people.map((person,i)=><pre className="ppeJson" key={i}>{JSON.stringify(person,null,2)}</pre>)}</div>}
 </section>;
}
