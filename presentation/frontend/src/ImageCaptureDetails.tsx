import {useEffect,useState} from "react";
import {getImageCaptureMetadata,type ImageCaptureMetadata} from "./api";
export default function ImageCaptureDetails({kind,id}:{kind:"ppe"|"face";id:string}){
 const [data,setData]=useState<ImageCaptureMetadata|null>(null);
 const [error,setError]=useState(false);
 useEffect(()=>{let active=true;setData(null);setError(false);
 getImageCaptureMetadata(kind,id).then(v=>{if(active)setData(v)})
 .catch(()=>{if(active)setError(true)});
 return()=>{active=false}},[kind,id]);
 return <section className="evidenceItem"><h4>Capture metadata &amp; Neo4j projection</h4>
 {error?<p className="muted">Capture metadata unavailable or access denied.</p>:
 !data?<p className="muted">Loading capture metadata…</p>:
 !data.capture_metadata?<p className="muted">No stored camera/capture-time metadata for this observation. Image-only inference remains valid.</p>:
 <><div className="standaloneMeta"><div><small>Declared camera</small><strong>{data.capture_metadata.camera_id}</strong></div>
 <div><small>Capture time</small><strong>{new Date(data.capture_metadata.captured_at).toLocaleString()}</strong></div>
 <div><small>Zone</small><strong>{data.capture_metadata.zone_id}</strong></div></div>
 <p className="muted">Provenance: {data.capture_metadata.provenance.replaceAll("_"," ")}. Camera source has not been independently verified.</p>
 <p>Neo4j: <b>{data.graph_projection?.graph_status??"NOT PROJECTED"}</b> · Evidence: {data.graph_projection?.event_id??"Unavailable"}</p>
 <p className="muted">Correlation: {data.graph_projection?.correlation_status??"NOT RUN"} · Decision: {data.graph_projection?.decision_status??"NOT RUN"}</p></>}</section>
}
