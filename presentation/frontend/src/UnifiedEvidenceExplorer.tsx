import PPEObservationViewer from "./PPEObservationViewer";
import FaceObservationViewer from "./FaceObservationViewer";
import type {UnifiedCorrelationGroup,PublishedSSH,MaintenanceEvent,EnvironmentalEvent} from "./api";

type Props={
 group:UnifiedCorrelationGroup;
 ssh:PublishedSSH[];
 maintenance:MaintenanceEvent[];
 environment:EnvironmentalEvent[];
};
export default function UnifiedEvidenceExplorer({group,ssh,maintenance,environment}:Props){
 return <section><h4>Unified Evidence Explorer</h4>
 <p className="muted">Original retained observations, not regenerated model predictions. Individual source assessments may predate this correlation.</p>
 {group.evidence.map(ref=>{
 const key=ref.kind+":"+ref.observation_id;
 if(ref.kind==="ppe")return <details key={key}><summary>PPE · {ref.observation_id}</summary><PPEObservationViewer id={ref.observation_id}/></details>;
 if(ref.kind==="face")return <details key={key}><summary>Face Recognition · {ref.observation_id}</summary><FaceObservationViewer id={ref.observation_id}/></details>;
 if(ref.kind==="ssh"){
 const item=ssh.find(x=>x.event_id===ref.observation_id);
 return <details key={key}><summary>SSH · {ref.observation_id}</summary>{item?<div className="evidenceItem">
 <p>Detector: {item.evidence_state} · Source IP: {item.source_ip??"Unavailable"} · Server: {item.server_id}</p>
 <p>Original window: {item.window_start??"Unavailable"} · Received: {new Date(item.received_at).toLocaleString()}</p>
 <p>Usernames: {item.usernames?.join(", ")||"Unavailable"} · Detector votes: {item.detector_votes}</p>
 <pre className="ppeJson">{JSON.stringify(item.evidence,null,2)}</pre>
 <p>Saved standalone Decision: {item.decision_record?.decision.severity??"NOT RUN"}</p>
 </div>:<p className="muted">SSH source unavailable or not returned by the authorized Evidence API.</p>}</details>
 }
 if(ref.kind==="maintenance"){
 const item=maintenance.find(x=>x.event_id===ref.observation_id);
 return <details key={key}><summary>Predictive Maintenance · {ref.observation_id}</summary>{item?<div className="evidenceItem">
 <p>{item.assessment.assessment} · Server: {item.server_id} · Drive: {item.assessment.serial_number}</p>
 <p>Observed: {new Date(item.assessment.observation_timestamp).toLocaleString()} · Received: {new Date(item.received_at).toLocaleString()}</p>
 <p>Seven-day risk: {(item.assessment.failure_probability*100).toFixed(2)}%</p>
 <details><summary>SMART history ({item.history.length} observations)</summary><div className="maintenanceHistory" role="table"><div className="maintenanceHistoryRow maintenanceHistoryHeader" role="row"><span>Date</span><span>SMART 5</span><span>SMART 198</span><span>Temperature</span></div>{item.history.map((r,i)=><div className="maintenanceHistoryRow" role="row" key={i}><span>{r.date.slice(0,10)}</span><span>{r.smart_5_raw??"—"}</span><span>{r.smart_198_raw??"—"}</span><span>{r.smart_194_raw??"—"}</span></div>)}</div></details>
 </div>:<p className="muted">Maintenance source unavailable or not returned by the authorized Evidence API.</p>}</details>
 }
 if(ref.kind==="environment"){
 const item=environment.find(x=>x.event_id===ref.observation_id);
 return <details key={key}><summary>Environmental Monitoring · {ref.observation_id}</summary>{item?<div className="evidenceItem">
 <p>{item.assessment.assessment} · Sensor: {item.sensor_id} · Zone: {item.zone_id}</p>
 <p>Received: {new Date(item.received_at).toLocaleString()}</p>
 <div className="maintenanceHistory" role="table"><div className="maintenanceHistoryRow maintenanceHistoryHeader" role="row"><span>Timestamp</span><span>Temperature °C</span><span>Humidity %</span><span>Assessment</span></div>{item.history.map((r,i)=><div className="maintenanceHistoryRow" role="row" key={i}><span>{new Date(r.timestamp).toLocaleString()}</span><span>{r.temperature_c??"—"}</span><span>{r.humidity_pct??"—"}</span><span>{item.workflow.reading_states?.[i]??"Not available"}</span></div>)}</div>
 </div>:<p className="muted">Environmental source unavailable or not returned by the authorized Evidence API.</p>}</details>
 }
 return <p key={key}>Unsupported Evidence type: {ref.kind}</p>
 })}
 </section>
}
