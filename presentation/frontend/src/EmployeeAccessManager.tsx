import {useEffect,useState} from "react";
import {getCurrentUser,getEmployees,registerEmployee,changeEmployeeAccess,type EmployeeAccess} from "./api";
const zones=["ZONE-A","ZONE-B","ZONE-C"];
export default function EmployeeAccessManager(){
 const [isAdmin,setIsAdmin]=useState(false),[items,setItems]=useState<EmployeeAccess[]>([]);
 const [selectedId,setSelectedId]=useState("");
 const [person,setPerson]=useState(""),[role,setRole]=useState("DATA_CENTER_TECHNICIAN");
 const [busy,setBusy]=useState(false),[error,setError]=useState(""),[notice,setNotice]=useState("");
 const [showRegistration,setShowRegistration]=useState(false);
 const selected=items.find(item=>item.person_id===selectedId);
 const refresh=async()=>setItems(await getEmployees());
 useEffect(()=>{let active=true;getCurrentUser().then(user=>{if(active&&user.roles.includes("administrator")){setIsAdmin(true);getEmployees().then(v=>{if(active)setItems(v)}).catch(()=>{if(active)setError("Employee directory unavailable")})}}).catch(()=>{});return()=>{active=false}},[]);
 async function run(action:()=>Promise<unknown>){setBusy(true);setError("");setNotice("");try{await action();await refresh();setNotice("Employee directory updated. Reopen the face observation to refresh authorization.")}catch(e){setError(e instanceof Error?e.message:"Update failed")}finally{setBusy(false)}}
 async function register(e:React.FormEvent){e.preventDefault();const id=person.trim().toUpperCase();setBusy(true);setError("");setNotice("");try{await registerEmployee(id,role.trim().toUpperCase());await refresh();setSelectedId(id);setPerson("");setShowRegistration(false);setNotice("Employee registered. Assign zones below if appropriate.")}catch(e){setError(e instanceof Error?e.message:"Registration failed")}finally{setBusy(false)}}
 if(!isAdmin)return null;
 return <section className="panel ppeLab"><h3>Employee Access Management</h3><p className="muted">Administrator-only · synthetic Neo4j topology · audited permission changes. Face enrollment is managed separately.</p>
 <div className="eventForm"><label className="eventFormWide">Select registered employee
 <select value={selectedId} onChange={e=>{setSelectedId(e.target.value);setNotice("");setError("")}}>
 <option value="">Choose an employee…</option>
 {items.map(item=><option key={item.person_id} value={item.person_id}>{item.person_id} · {item.role}</option>)}
 </select></label></div>
 {selected&&<div className="evidenceItem"><h4>{selected.person_id} · {selected.role}</h4><p className="muted">Authorized zones: {selected.authorized_zones.length?selected.authorized_zones.join(", "):"None"}</p><div className="accessZones">{zones.map(zone=><button key={zone} type="button" disabled={busy} onClick={()=>{const action=selected.authorized_zones.includes(zone)?"REVOKE":"GRANT";if(window.confirm(`${action} ${selected.person_id} access to ${zone}?`))void run(()=>changeEmployeeAccess(selected.person_id,zone,action))}}>{zone}: {selected.authorized_zones.includes(zone)?"Revoke":"Grant"}</button>)}</div></div>}
 <button type="button" className="closeIncident" onClick={()=>setShowRegistration(v=>!v)} aria-expanded={showRegistration}>{showRegistration?"− Cancel registration":"+ Register new employee"}</button>
 {showRegistration&&<form onSubmit={e=>void register(e)} className="eventForm accessForm">
 <label>New employee ID <input value={person} onChange={e=>setPerson(e.target.value.toUpperCase())} placeholder="P006" pattern="P[0-9]{3,8}" required/></label>
 <label>Role <input value={role} onChange={e=>setRole(e.target.value.toUpperCase())} pattern="[A-Z][A-Z0-9_]*" required/></label>
 <button disabled={busy}>Register employee</button></form>}
 {error&&<p role="alert" className="error">{error}</p>}{notice&&<p role="status">{notice}</p>}
 </section>;
}