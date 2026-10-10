import {useState} from "react";
import {getAuditIntegrity,type AuditIntegrityResult} from "./api";

export default function AuditIntegrityPanel(){
 const [result,setResult]=useState<AuditIntegrityResult|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(false);
 async function check(){
  setLoading(true);setError("");setResult(null);
  try{setResult(await getAuditIntegrity())}
  catch(e){setError(e instanceof Error?e.message:"Integrity verification unavailable")}
  finally{setLoading(false)}
 }
 return <section className="panel auditIntegrityPanel">
  <div className="analyticsFilterHeader"><div><h3>Audit integrity verification</h3><p className="muted">Administrator-only · verifies the complete local human-review hash chain.</p></div>
   <button type="button" disabled={loading} onClick={()=>void check()}>{loading?"Verifying…":"Verify audit integrity"}</button></div>
  {result&&<div className="auditIntegrityResult" role="status"><strong className={result.status==="PASS"?"auditPass":"auditFailed"}>{result.status}</strong><span>Records checked: {result.checked}</span>
   {result.audit_id&&<p>First affected record: <code>{result.audit_id}</code></p>}
   {result.reason&&<p>Reason: {result.reason}</p>}
   {result.head_hash&&<details><summary>Chain head hash</summary><code>{result.head_hash}</code></details>}
   {result.limitation&&<p className="muted">{result.limitation}</p>}</div>}
  {error&&<p role="alert" className="muted">{error.includes("(403)")?"Administrator permission is required to inspect the global audit chain.":error.includes("(401)")?"Sign in to verify audit integrity.":error}</p>}
  <p className="muted">A PASS result checks local record consistency only. It cannot detect database replacement or removal of final records without a trusted external checkpoint.</p>
 </section>;
}
