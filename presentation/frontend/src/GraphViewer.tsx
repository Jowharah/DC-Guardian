import {useEffect,useState} from "react";
import {getIncidentGraph,type IncidentGraph} from "./api";

export default function GraphViewer({scenarioId}:{scenarioId:string}){
 const [graph,setGraph]=useState<IncidentGraph|null>(null);
 const [selected,setSelected]=useState<string|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{let active=true;setGraph(null);setSelected(null);setError("");getIncidentGraph(scenarioId).then(data=>{if(active)setGraph(data)}).catch(()=>{if(active)setError("Neo4j graph unavailable. Verify database connectivity.")});return()=>{active=false}},[scenarioId]);
 if(error)return <div className="panel muted" role="status">{error}</div>;
 if(!graph)return <div className="panel muted">Loading graph…</div>;
 if(graph.nodes.length===0)return <div className="panel muted">No graph nodes found for this scenario.</div>;
 const shown=graph.nodes.slice(0,40),ids=new Set(shown.map(n=>n.id));
 const positions=new Map(shown.map((n,i)=>[n.id,{x:350+245*Math.cos(i*2*Math.PI/shown.length),y:230+175*Math.sin(i*2*Math.PI/shown.length)}]));
 const node=shown.find(n=>n.id===selected);
 return <div className="panel"><p className="muted">Neo4j read-only neighborhood · {graph.nodes.length} nodes · {graph.edges.length} relationships. Select a node to inspect approved properties.</p><svg className="graphCanvas" viewBox="0 0 700 460" role="img" aria-label="Scenario infrastructure graph">{graph.edges.filter(e=>ids.has(e.source)&&ids.has(e.target)).map(e=>{const a=positions.get(e.source)!,b=positions.get(e.target)!;return <g key={e.id}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="#8392CF" strokeWidth="1.5"/><text x={(a.x+b.x)/2} y={(a.y+b.y)/2} fill="#A794B0" fontSize="9" textAnchor="middle">{e.type}</text></g>})}{shown.map(n=>{const p=positions.get(n.id)!;return <g key={n.id} onClick={()=>setSelected(n.id)} tabIndex={0} role="button" aria-label={`Inspect ${n.label}`} onKeyDown={e=>{if(e.key==="Enter"||e.key===" ")setSelected(n.id)}}><circle cx={p.x} cy={p.y} r="25" fill={selected===n.id?"#742A79":"#524184"} stroke="#E3B8E0" strokeWidth="2"/><text x={p.x} y={p.y+39} fontSize="11" fill="#F4E5F3" textAnchor="middle">{n.label.slice(0,22)}</text></g>})}</svg>{node&&<div className="evidenceItem"><b>{node.type}: {node.label}</b><dl>{Object.entries(node.properties).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>)}</dl></div>}</div>;
}
