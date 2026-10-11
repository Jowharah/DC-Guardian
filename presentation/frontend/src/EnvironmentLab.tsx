import {useEffect,useState} from "react";
import PostPublicationCheck from "./PostPublicationCheck";
import {getTopologyOptions,validateEnvironment,type EnvironmentalAssessment} from "./api";
export default function EnvironmentLab(){
 const [zones,setZones]=useState<{zone_id:string;sensors:string[]}[]>([]);
 const [zone,setZone]=useState("ZONE-B"),[sensor,setSensor]=useState("");
 const [file,setFile]=useState<File|null>(null),[publish,setPublish]=useState(true);
 const [result,setResult]=useState<{published:boolean;assessments:EnvironmentalAssessment[];events:{event_id:string;assessment:EnvironmentalAssessment;workflow:{stages:{stage:string;status:string;detail?:string}[]}}[]}|null>(null);
 const [busy,setBusy]=useState(false),[error,setError]=useState("");
 useEffect(()=>{getTopologyOptions().then(setZones).catch(()=>setError("Topology unavailable"))},[]);
 const sensors=zones.find(x=>x.zone_id===zone)?.sensors??[];
 useEffect(()=>{setSensor(v=>sensors.includes(v)?v:sensors[0]??"")},[zone,zones]);
 async function submit(e:React.FormEvent){e.preventDefault();if(!file||!sensor)return;setBusy(true);setError("");setResult(null);
 try{setResult(await validateEnvironment(file,zone,sensor,publish))}
 catch(e){setError(e instanceof Error?e.message:"Sensor validation failed")}finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>Environmental Sensor Validation</h3>
 <p className="muted">Approved timestamped sensor CSV · frozen environmental threshold detector · one-click Evidence, Neo4j, and correlation. Standalone Decision severity is not assigned.</p>
 <form className="eventForm" onSubmit={e=>void submit(e)}>
 <label>Zone<select value={zone} onChange={e=>setZone(e.target.value)}>{zones.map(z=><option key={z.zone_id}>{z.zone_id}</option>)}</select></label>
 <label>Sensor<select value={sensor} onChange={e=>setSensor(e.target.value)}>{sensors.map(x=><option key={x}>{x}</option>)}</select></label>
 <label className="eventFormWide">Sensor CSV<input type="file" accept=".csv,text/csv" required onChange={e=>setFile(e.target.files?.[0]??null)}/></label>
 <label className="eventFormWide retentionLabel"><input type="checkbox" checked={publish} onChange={e=>setPublish(e.target.checked)}/> Share assessed readings to Monitoring Feed</label>
 <button disabled={!file||!sensor||busy}>{busy?"Processing sensor readings…":"Validate Environmental Readings"}</button></form>
 <p className="muted">Required columns: timestamp, temperature_c, humidity_pct. Use ISO-8601 timestamps with timezone; up to 500 rows, 1 MiB. Missing individual measurements are allowed.</p>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>Environmental detector results</h4><p>{result.assessments.length} readings · {result.assessments.filter(x=>x.anomaly_detected).length} anomalous · {result.events.length} published</p>
 {result.assessments.map((x,i)=><details key={i}><summary>{x.assessment.replaceAll("_"," ")} · {x.observation_timestamp}</summary><p>Temperature: {x.measurements.temperature_c??"—"} °C · Humidity: {x.measurements.humidity_pct??"—"}%</p>
 {result.events[i]&&<p>Pipeline: {result.events[i].workflow.stages.map(s=>s.stage+" "+s.status).join(" · ")}</p>}</details>)}</div>}{result?.published&&result.events.length>0&&<PostPublicationCheck kind="environment" ids={result.events.map(e=>e.event_id)}/> }</section>;
}
