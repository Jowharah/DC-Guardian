import {useEffect,useState} from "react";
import {getUnifiedCorrelations,getOperationalCorrelations,getPhysicalImageCandidates,getFaceSSHCandidates,
 type UnifiedCorrelationGroup,type OperationalCorrelation,type PhysicalImageCandidate,type FaceSSHCandidate} from "./api";

type Props={openMonitoring:()=>void;openUnified:(group:UnifiedCorrelationGroup)=>void};
export default function CorrelationTestingPanel({openMonitoring,openUnified}:Props){
 const [groups,setGroups]=useState<UnifiedCorrelationGroup[]>([]);
 const [operational,setOperational]=useState<OperationalCorrelation[]>([]);
 const [physical,setPhysical]=useState<PhysicalImageCandidate[]>([]);
 const [faceSSH,setFaceSSH]=useState<FaceSSHCandidate[]>([]);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState("");
 const [checkedAt,setCheckedAt]=useState<string|null>(null);
 async function refresh(){
   setLoading(true);setError("");
   try{
     const [u,o,p,f]=await Promise.all([
       getUnifiedCorrelations(),getOperationalCorrelations(),
       getPhysicalImageCandidates(),getFaceSSHCandidates()]);
     setGroups(u);setOperational(o);setPhysical(p);setFaceSSH(f);
     setCheckedAt(new Date().toLocaleTimeString());
   }catch(e){setError(e instanceof Error?e.message:"Correlation services unavailable")}
   finally{setLoading(false)}
 }
 useEffect(()=>{
   let active=true;
   async function poll(){
     try{
       const [u,o,p,f]=await Promise.all([
         getUnifiedCorrelations(),getOperationalCorrelations(),
         getPhysicalImageCandidates(),getFaceSSHCandidates()]);
       if(!active)return;
       setGroups(u);setOperational(o);setPhysical(p);setFaceSSH(f);
       setCheckedAt(new Date().toLocaleTimeString());setError("");
     }catch(e){if(active)setError(e instanceof Error?e.message:"Correlation services unavailable")}
   }
   void poll();
   const interval=setInterval(()=>void poll(),5000);
   return()=>{active=false;clearInterval(interval)};
 },[]);
 const combined=new Set(groups.filter(g=>g.domains.length>=3).flatMap(g=>g.source_candidate_ids));
 const pairCount=operational.filter(x=>!combined.has(x.id)).length+
   physical.filter(x=>!combined.has(x.id)).length+
   faceSSH.filter(x=>!combined.has(x.id)).length;
 return <div className="panel">
   <p>Published Evidence is checked against the existing correlation contracts. Sequential uploads do not automatically establish a relationship.</p>
   <p className="muted">Automatically refreshes every five seconds while Scenario Lab is open. Only saved, eligible candidates appear; historical and unverified timestamps retain their provenance limitations.</p>
   <p><b>{groups.filter(g=>g.domains.length>=3).length}</b> multi-domain groups · <b>{pairCount}</b> separate two-domain candidates</p>
   {checkedAt&&<p className="muted">Last checked: {checkedAt}</p>}
   {error&&<p role="alert" className="error">Correlation check unavailable: {error}</p>}
   {!error&&groups.length===0&&pairCount===0&&<p className="muted">No eligible correlation candidates currently returned. Published standalone Evidence remains in Monitoring Center.</p>}
   {groups.filter(g=>g.domains.length>=3).map(g=><div key={g.id} className="evidenceItem">
     <p><b>{g.domains.join(" + ")}</b> · {g.zone_id}</p>
     <p>{g.evidence.length} Evidence records · {g.edges.length} explicit source links · Candidate only</p>
     <button type="button" onClick={()=>openUnified(g)}>Open unified investigation</button>
   </div>)}
   {pairCount>0&&<p className="muted">Two-domain investigations are available in Monitoring Center. Groups already included above are not counted twice.</p>}
   <button type="button" disabled={loading} onClick={()=>void refresh()}>{loading?"Checking…":"Check correlations now"}</button>
   <button type="button" onClick={openMonitoring}>Open Monitoring Center</button>
 </div>;
}
