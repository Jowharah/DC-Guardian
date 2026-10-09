import {useEffect,useState} from "react";
import {getTopologyOptions,validateMaintenance,type MaintenanceValidation} from "./api";
export default function MaintenanceLab(){
 const [zones,setZones]=useState<{zone_id:string;servers:string[]}[]>([]);
 const [zone,setZone]=useState("ZONE-B"),[server,setServer]=useState("");
 const [file,setFile]=useState<File|null>(null),[publish,setPublish]=useState(true);
 const [result,setResult]=useState<MaintenanceValidation|null>(null),[error,setError]=useState(""),[busy,setBusy]=useState(false);
 useEffect(()=>{getTopologyOptions().then(setZones).catch(()=>setError("Topology unavailable"))},[]);
 const servers=zones.find(x=>x.zone_id===zone)?.servers??[];
 useEffect(()=>{setServer(s=>servers.includes(s)?s:servers[0]??"")},[zone,zones]);
 async function submit(e:React.FormEvent){e.preventDefault();if(!file||!server)return;setBusy(true);setError("");setResult(null);
 try{setResult(await validateMaintenance(file,zone,server,publish))}
 catch(e){setError(e instanceof Error?e.message:"Maintenance validation failed")}
 finally{setBusy(false)}}
 return <section className="panel ppeLab"><h3>Predictive Maintenance Validation</h3>
 <p className="muted">Approved SMART CSV · frozen Temporal RF v2 · one drive, at least 8 historical observations. Optional publication runs Evidence → Neo4j → correlation → supported Operations Response. No invented Decision severity.</p>
 <form className="eventForm" onSubmit={e=>void submit(e)}>
 <label>Zone<select value={zone} onChange={e=>setZone(e.target.value)}>{zones.map(z=><option key={z.zone_id}>{z.zone_id}</option>)}</select></label>
 <label>Server<select value={server} onChange={e=>setServer(e.target.value)}>{servers.map(x=><option key={x}>{x}</option>)}</select></label>
 <label className="eventFormWide">SMART history CSV<input type="file" accept=".csv,text/csv" required onChange={e=>setFile(e.target.files?.[0]??null)}/></label>
 <label className="eventFormWide retentionLabel"><input type="checkbox" checked={publish} onChange={e=>setPublish(e.target.checked)}/> Share assessment to Monitoring Feed and run supported pipeline stages</label>
 <button disabled={busy||!file||!server}>{busy?"Processing SMART history…":"Validate SMART history"}</button></form>
 <p className="muted">Columns: date, serial_number, smart_5_raw, smart_9_raw, smart_192_raw, smart_193_raw, smart_194_raw, smart_198_raw, smart_4_raw, smart_12_raw. One drive per upload; up to 4 MiB.</p>
 {error&&<p role="alert" className="error">{error}</p>}
 {result&&<div className="evidenceItem"><h4>Frozen Temporal RF v2 · {result.assessment.assessment}</h4>
 <p>Drive: {result.assessment.serial_number} · Estimated 7-day failure risk score: {(result.assessment.failure_probability*100).toFixed(2)}% · Threshold: {(result.assessment.operating_threshold*100).toFixed(0)}%</p>
 <p>{result.published?"Published to Monitoring Center":"Preview only"} · {result.history.length} measurements</p>
 {result.workflow&&<details><summary>Pipeline stage results</summary>{result.workflow.stages.map(x=><p key={x.stage}>{x.stage}: {x.status} · {x.detail}</p>)}</details>}
 <p className="muted">Model score is not a calibrated certainty of failure. No raw CSV retained.</p></div>}</section>
}
