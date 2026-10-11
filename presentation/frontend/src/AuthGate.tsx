import {useState} from "react";
import {clearCredentials,getCurrentUser,setCredentials} from "./api";
import App from "./App";

export default function AuthGate(){
 const [user,setUser]=useState<{username:string;roles:string[];zones:string[]}|null>(null);
 const [name,setName]=useState("");
 const [password,setPassword]=useState("");
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function login(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError("");
  setCredentials(name,password);
  try{const current=await getCurrentUser();setUser(current);setPassword("")}
  catch{clearCredentials();setError("Login failed. Check the local operator account and FastAPI settings.")}
  finally{setBusy(false)}
 }
 if(user)return <><div className="authBanner"><span>Signed in: {user.username} · {user.roles.join(", ")} · Zones: {user.zones.join(", ")}</span><button type="button" onClick={()=>{clearCredentials();setUser(null)}}>Sign out</button></div><App/></>;
 return <div className="authScreen"><form className="panel authForm" onSubmit={e=>void login(e)}><p className="eyebrow">DC-GUARDIAN · LOCAL PROTOTYPE</p><h1>Operator sign in</h1><p className="muted">Sign in with the account configured on your FastAPI server. Credentials stay in this browser tab's memory.</p><label>Username<input autoComplete="username" value={name} onChange={e=>setName(e.target.value)} required/></label><label>Password<input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required/></label>{error&&<p role="alert" className="error">{error}</p>}<button disabled={busy} type="submit">{busy?"Signing in…":"Sign in"}</button><p className="muted">Local HTTP Basic development authentication only. Do not expose this service beyond 127.0.0.1.</p></form></div>;
}
