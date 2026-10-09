import ImageCaptureControls,{type CaptureInput,declareImageCapture} from "./ImageCaptureControls";
import {useEffect,useState} from "react";
import PostPublicationCheck from "./PostPublicationCheck";
import {validateFaceImage,type FaceImageResult} from "./api";
export default function FaceImageLab(){
 const [capture,setCapture]=useState<CaptureInput|null>(null);
 const [file,setFile]=useState<File|null>(null),[preview,setPreview]=useState("");
 const [retain,setRetain]=useState(false),[zone,setZone]=useState("ZONE-B");
 const [result,setResult]=useState<FaceImageResult|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{if(!file){setPreview("");return}const url=URL.createObjectURL(file);setPreview(url);return()=>URL.revokeObjectURL(url)},[file]);
 async function run(){if(!file)return;setBusy(true);setError("");setResult(null);try{const r=await validateFaceImage(file,retain,zone);if(capture&&r.observation){await declareImageCapture("face",r.observation.observation_id,capture.camera,new Date(capture.time).toISOString())}setResult(r)}catch(e){setError(e instanceof Error?e.message:"Face inference unavailable")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>Face recognition image validation</h3><p className="muted">Approved test images only · frozen RetinaFace + ArcFace · private local enrollment. Recognition is not zone authorization and does not create an incident.</p>
 <div className="eventForm"><label className="eventFormWide">JPEG or PNG (maximum 8 MiB)<input type="file" accept="image/png,image/jpeg" onChange={e=>{setFile(e.target.files?.[0]??null);setResult(null)}}/></label>
 </div>{preview&&<div className="ppePreview"><img src={preview} alt="Selected face validation image"/></div>}
 <div className="eventForm"><label className="eventFormWide retentionLabel"><input type="checkbox" checked={retain} onChange={e=>setRetain(e.target.checked)}/> Retain approved test image in protected local Face evidence storage</label>
 {retain&&<label className="eventFormWide">Assigned zone <select value={zone} onChange={e=>setZone(e.target.value)}><option>ZONE-A</option><option>ZONE-B</option><option>ZONE-C</option></select></label>}
 </div>{retain&&<ImageCaptureControls zone={zone} onChange={setCapture}/>}<button disabled={!file||busy} onClick={()=>void run()}>{busy?"Running frozen face model…":"Validate face image"}</button>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>{result.assessment.recognition_status}</h4><p>Identity: <b>{result.assessment.person_id}</b> · Similarity: {result.assessment.similarity?.toFixed(3)??"N/A"} · Cosine distance: {result.assessment.distance?.toFixed(3)??"N/A"}</p><p className="muted">Authorization: NOT EVALUATED · {result.image_stored?"Retained for Monitoring Center review.":"Not retained."}</p></div>}
 {result?.image_stored&&result.observation&&<PostPublicationCheck kind="face" ids={[result.observation.observation_id]}/> }</section>
}
