import {useEffect,useState} from "react";
import {validateFaceImage,type FaceImageResult} from "./api";
export default function FaceImageLab(){
 const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState("");
 const [retain,setRetain]=useState(false),[zone,setZone]=useState("ZONE-B");
 const [result,setResult]=useState<FaceImageResult|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{if(!file){setPreview("");return}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url)},[file]);
 async function run(){if(!file)return;setBusy(true);setError("");setResult(null);try{setResult(await validateFaceImage(file,retain,zone))}catch(e){setError(e instanceof Error?e.message:"Face inference unavailable")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>Face recognition image validation</h3><p className="muted">Approved test images only · frozen RetinaFace + ArcFace · private local enrollment. Recognition is not zone authorization and does not create an incident.</p>
 <label className="ppeFileLabel">JPEG or PNG (maximum 8 MiB)<input type="file" accept="image/png,image/jpeg" onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null)}}/></label>
 {preview&&<div className="ppePreview"><img src={preview} alt="Selected face validation image"/></div>}
 <label><input type="checkbox" checked={retain} onChange={e=>setRetain(e.target.checked)}/> Retain approved test image in protected local Face evidence storage</label>
 {retain&&<label>Assigned zone <select value={zone} onChange={e=>setZone(e.target.value)}><option>ZONE-A</option><option>ZONE-B</option><option>ZONE-C</option></select></label>}
 <button disabled={!file||busy} onClick={()=>void run()}>{busy?"Running frozen face model…":"Validate face image"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>{result.assessment.recognition_status}</h4><p>Identity: <b>{result.assessment.person_id}</b> · Similarity: {result.assessment.similarity?.toFixed(3)??"N/A"} · Cosine distance: {result.assessment.distance?.toFixed(3)??"N/A"}</p><p className="muted">Authorization: NOT EVALUATED · {result.image_stored?"Retained for Monitoring Center review.":"Not retained."}</p></div>}
 </section>
}
