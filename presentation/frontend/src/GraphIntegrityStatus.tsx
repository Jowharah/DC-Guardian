import {useEffect,useState} from "react";
import {getGraphIntegrity,type GraphIntegrity} from "./api";

export default function GraphIntegrityStatus({scenarioId}:{scenarioId:string}){
 const [result,setResult]=useState<GraphIntegrity|null>(null);
 const [error,setError]=useState(false);
 const [refresh,setRefresh]=useState(0);
 useEffect(()=>{
  let active=true;setResult(null);setError(false);
  getGraphIntegrity(scenarioId).then(value=>{if(active)setResult(value)}).catch(()=>{if(active)setError(true)});
  return()=>{active=false};
 },[scenarioId,refresh]);
 return <div className="graphIntegrity" role="status" aria-live="polite">
  <div className="incidentTop"><div><b>Graph integrity</b><p className="muted">Checks stored Evidence event nodes and SSH source links.</p></div>
  <button type="button" className="closeIncident" onClick={()=>setRefresh(n=>n+1)}>Recheck</button></div>
  {error?<p className="muted">Integrity check unavailable. This is not a PASS.</p>
   :!result?<p className="muted">Checking graph…</p>
   :<><p className={result.status==="PASS"?"integrityPass":"integrityIncomplete"}>{result.status==="PASS"?"PASS — checked relationships present":"INCOMPLETE — graph evidence missing"}</p>
    <p className="muted">{result.observed_event_count} observed / {result.expected_event_count} expected event nodes</p>
    {result.missing_event_ids.length>0&&<><b>Missing events</b><ul>{result.missing_event_ids.map(id=><li key={id}>{id}</li>)}</ul></>}
    {result.missing_ssh_source_relationships.length>0&&<><b>SSH events without SourceIP link</b><ul>{result.missing_ssh_source_relationships.map(id=><li key={id}>{id}</li>)}</ul></>}
   </>}
  <small className="muted">A PASS covers these specific integrity checks only; it does not certify the entire Neo4j graph.</small>
 </div>;
}
