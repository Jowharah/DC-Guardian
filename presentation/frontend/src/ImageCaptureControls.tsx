import {useEffect,useState} from "react";
import {getCameraTopology} from "./api";
export type CaptureInput={camera:string;time:string};
export default function ImageCaptureControls({zone,onChange}:{zone:string;onChange:(value:CaptureInput|null)=>void}){
 const [enabled,setEnabled]=useState(false);
 const [camera,setCamera]=useState("");
 const [time,setTime]=useState("");
 const [ack,setAck]=useState(false);
 const [cameras,setCameras]=useState<Record<string,string[]>>({});
 const [topologyError,setTopologyError]=useState("");
 useEffect(()=>{getCameraTopology().then(rows=>setCameras(Object.fromEntries(rows.map(r=>[r.zone_id,r.cameras])))).catch(()=>setTopologyError("Registered camera topology unavailable"))},[]);
 useEffect(()=>{setCamera("");onChange(null)},[zone]);
 useEffect(()=>{
   onChange(enabled&&ack&&camera&&time?{camera,time}:null);
 },[enabled,ack,camera,time,zone,onChange]);
 return <div className="eventForm">
   <label className="eventFormWide retentionLabel"><input type="checkbox" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/> Declare controlled camera and capture time</label>
   {enabled&&<>
     <label>Camera<select value={camera} onChange={e=>setCamera(e.target.value)}>
       <option value="">Choose a camera…</option>
       {(cameras[zone]??[]).map(id=><option key={id} value={id}>{id}</option>)}
     </select></label>
     <label>Capture time (local)<input type="datetime-local" value={time} onChange={e=>setTime(e.target.value)}/></label>
     <label className="eventFormWide retentionLabel"><input type="checkbox" checked={ack} onChange={e=>setAck(e.target.checked)}/> I acknowledge that camera identity and capture time are operator-declared and unverified.</label>
     {topologyError&&<p role="alert">{topologyError}</p>}
     {enabled&&(cameras[zone]??[]).length===0&&!topologyError&&<p className="muted">No registered cameras available in this zone. Choose another zone or review topology.</p>}
     <p className="muted">Only registered cameras in the selected zone are accepted by the backend. Original image model results are unchanged.</p>
   </>}
 </div>;
}
