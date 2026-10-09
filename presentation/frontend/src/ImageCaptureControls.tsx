import {useState} from "react";
import {declareImageCapture} from "./api";
export type CaptureInput={camera:string;time:string};
export default function ImageCaptureControls({zone,onChange}:{zone:string;onChange:(value:CaptureInput|null)=>void}){
 const [enabled,setEnabled]=useState(false);
 const [camera,setCamera]=useState("");
 const [time,setTime]=useState("");
 const [ack,setAck]=useState(false);
 const cameras:Record<string,string[]>={"ZONE-B":["CAM-B-01"]};
 function change(next:CaptureInput|null){onChange(next)}
 return <div className="eventForm">
 <label className="eventFormWide retentionLabel"><input type="checkbox" checked={enabled} onChange={e=>{setEnabled(e.target.checked);change(null)}}/> Declare controlled camera and capture time</label>
 {enabled&&<><label>Camera<select value={camera} onChange={e=>{setCamera(e.target.value);change(null)}}>
 <option value="">Choose a camera…</option>{(cameras[zone]??[]).map(id=><option key={id} value={id}>{id}</option>)}</select></label>
 <label>Capture time (local)<input type="datetime-local" value={time} onChange={e=>{setTime(e.target.value);change(null)}}/></label>
 <label className="eventFormWide retentionLabel"><input type="checkbox" checked={ack} onChange={e=>{setAck(e.target.checked);change(null)}}/> I acknowledge that camera identity and capture time are operator-declared and unverified.</label>
 {ack&&camera&&time&&<button type="button" onClick={()=>change({camera,time})}>Use declared capture metadata</button>}
 <p className="muted">Only registered cameras in the selected zone are accepted by the backend. Original image model results are unchanged.</p></>}
 </div>;
}
export {declareImageCapture};
