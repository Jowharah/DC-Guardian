import {useEffect,useState} from "react";
import {getCurrentUser,getEmployees,registerEmployee,changeEmployeeAccess,type EmployeeAccess} from "./api";
const zones=["ZONE-A","ZONE-B","ZONE-C"];
export default function EmployeeAccessManager(){
 const [isAdmin,setIsAdmin]=useState(false),[items,setItems]=useState<EmployeeAccess[]>([]);
 const [person,setPerson]=useState(""),[role,setRole]=useState("DATA_CENTER_TECHNICIAN");
 const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const refresh=async()=>setItems(await getEmployees());
 useEffect(()=>{let active=true;getCurrentUser().then(user=>{if(active&&user.roles.includes("administrator")){setIsAdmin(true);getEmployees().then(v=>{if(active)setItems(v)}).catch(()=>{if(active)setError("Employee directory unavailable")})}}).catch(()=>{});return()=>{active=false}},[]);
 async function run(action:()=>Promise<unknown>){setBusy(true);setError("");setNotice("");try{await action();await refresh();setNotice("Access directory updated. Reopen the face observation to refresh authorization.")}catch(e){setError(e instanceof Error?e.message:"Update failed")}finally{setBusy(false)}}
 if(!isAdmin)return null;
 return <section className="panel ppeLab"><h3>Employee Access Management</h3><p className="muted">Administrator-only · synthetic Neo4j topology · audited permission changes. Does not enroll faces or modify recognition embeddings.</p>
 <form onSubmit={e=>{e.preventDefault();void run(()=>registerEmployee(person.trim().toUpperCase(),role.trim().toUpperCase()))}} className="accessForm">
 <label>Employee ID <input value={person} onChange={e=>setPerson(e.target.value)} placeholder="P005" pattern="P[0-9]{3,8}" required/></label>
 <label>Role <input value={role} onChange={e=>setRole(e.target.value)} pattern="[A-Z][A-Z0-9_]*" required/></label>
 <button disabled={busy}>Register employee</button></form>
 {items.map(item=><div className="evidenceItem" key={item.person_id}><b>{item.person_id}</b> · {item.role}<p className="muted">Authorized zones: {item.authorized_zones.length?item.authorized_zones.join(", "):"None"}</p><div className="accessZones">{zones.map(zone=><button key={zone} type="button" disabled={busy} onClick={()=>{const action=item.authorized_zones.includes(zone)?"REVOKE":"GRANT";if(window.confirm(`${action} ${item.person_id} access to ${zone}?`))void run(()=>changeEmployeeAccess(item.person_id,zone,action))}}>{zone}: {item.authorized_zones.includes(zone)?"Revoke":"Grant"}</button>)}</div></div>)}
 {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
 </section>;
}
