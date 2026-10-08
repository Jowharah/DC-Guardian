import {useEffect,useMemo,useState} from "react";
import {getIncidentGraph,type IncidentGraph,type GraphNode} from "./api";

const palette:Record<string,string>={Event:"#742A79",Camera:"#524184",Person:"#794F65",Server:"#8392CF",Zone:"#A794B0",Sensor:"#6D83B6",Asset:"#7566AB",SourceIP:"#794F65"};
const width=960,height=560;
function nodeColor(type:string){return palette[type]??"#524184"}
function shortName(n:GraphNode){if(n.type==="Event"){const t=String(n.properties.event_type??"");if(t.includes("PPE"))return "PPE Assessment";if(t.includes("FACE"))return "Face Identification";if(t.includes("SSH"))return "SSH Assessment";if(t.includes("ENVIRONMENT"))return "Environmental Event";if(t.includes("STORAGE"))return "Maintenance Event";return "Evidence Event"}if(n.type==="Person")return "Person (restricted)";if(n.type==="SourceIP")return "Source IP (restricted)";const v=n.label;return v.length>23?v.slice(0,20)+"…":v}
export default function GraphViewer({scenarioId}:{scenarioId:string}){
 const [graph,setGraph]=useState<IncidentGraph|null>(null);
 const [selected,setSelected]=useState<string|null>(null);
 const [error,setError]=useState("");
 const [zoom,setZoom]=useState(1);
 const [offset,setOffset]=useState({x:0,y:0});
 const [drag,setDrag]=useState<{x:number;y:number;ox:number;oy:number}|null>(null);
 useEffect(()=>{let active=true;setGraph(null);setSelected(null);setError("");setZoom(1);setOffset({x:0,y:0});getIncidentGraph(scenarioId).then(data=>{if(active)setGraph(data)}).catch(()=>{if(active)setError("Neo4j graph unavailable. Verify database connectivity.")});return()=>{active=false}},[scenarioId]);
 const shown=useMemo(()=>graph?.nodes.slice(0,40)??[],[graph]);
 const positions=useMemo(()=>{
   const m=new Map<string,{x:number;y:number}>();
   if(!graph||!shown.length)return m;
   const order=["Zone","Rack","Server","Asset","Sensor","Camera","Person","SourceIP","Event"];
   const groups=new Map<string,GraphNode[]>();
   shown.forEach(n=>{const group=order.includes(n.type)?n.type:"Other";groups.set(group,[...(groups.get(group)??[]),n])});
   const columns=[...groups.keys()].sort((a,b)=>order.indexOf(a)-order.indexOf(b));
   columns.forEach((group,i)=>{const nodes=groups.get(group)!;nodes.forEach((n,j)=>m.set(n.id,{x:columns.length===1?width/2:95+i*770/(columns.length-1),y:height*(j+1)/(nodes.length+1)}))});
   return m;
 },[graph,shown]);
 const node=shown.find(n=>n.id===selected);
 const visibleIds=new Set(shown.map(n=>n.id));
 const edges=(graph?.edges??[]).filter(e=>visibleIds.has(e.source)&&visibleIds.has(e.target));
 const reset=()=>{setZoom(1);setOffset({x:0,y:0})};
 if(error)return <div className="panel muted" role="status">{error}</div>;
 if(!graph)return <div className="panel muted">Loading graph…</div>;
 if(!shown.length)return <div className="panel muted">No graph nodes found for this scenario.</div>;
 return <div className="panel graphPanel">
  <div className="graphToolbar"><div><b>Infrastructure relationships</b><p className="muted">{graph.nodes.length} nodes · {graph.edges.length} relationships · Neo4j read-only</p></div><div className="graphControls"><button type="button" onClick={()=>setZoom(z=>Math.min(2.5,+(z+.2).toFixed(2)))} aria-label="Zoom in">+</button><button type="button" onClick={()=>setZoom(z=>Math.max(.5,+(z-.2).toFixed(2)))} aria-label="Zoom out">−</button><button type="button" onClick={reset}>Reset</button></div></div>
  <div className="graphLegend">{[...new Set(shown.map(n=>n.type))].map(t=><span key={t}><i style={{background:nodeColor(t)}}/>{t}</span>)}</div>
  <svg className="graphCanvas" viewBox={`0 0 ${width} ${height}`} role="group" aria-label="Interactive Neo4j scenario infrastructure graph" onPointerDown={e=>{if(e.target===e.currentTarget){e.currentTarget.setPointerCapture(e.pointerId);setDrag({x:e.clientX,y:e.clientY,ox:offset.x,oy:offset.y})}}} onPointerMove={e=>{if(drag){const bounds=e.currentTarget.getBoundingClientRect();setOffset({x:drag.ox+(e.clientX-drag.x)*width/bounds.width,y:drag.oy+(e.clientY-drag.y)*height/bounds.height})}}} onPointerUp={()=>setDrag(null)} onPointerCancel={()=>setDrag(null)}>
   <defs><marker id="dcg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8392CF"/></marker></defs>
   <g transform={`translate(${offset.x} ${offset.y}) translate(${width/2} ${height/2}) scale(${zoom}) translate(${-width/2} ${-height/2})`}>
    {edges.map(e=>{const a=positions.get(e.source)!,b=positions.get(e.target)!;const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;const x1=a.x+dx*36/len,y1=a.y+dy*36/len,x2=b.x-dx*40/len,y2=b.y-dy*40/len;return <g key={e.id}><line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#8392CF" strokeWidth="2" opacity=".8" markerEnd="url(#dcg-arrow)"/><g transform={`translate(${(a.x+b.x)/2} ${(a.y+b.y)/2-10})`}><rect x={-Math.max(34,e.type.length*3.5+9)} y="-13" width={Math.max(68,e.type.length*7+18)} height="25" rx="8" fill="#160C20" stroke="#524184"/><text fill="#E3B8E0" fontSize="12" textAnchor="middle" y="4">{e.type}</text></g></g>})}
    {shown.map(n=>{const p=positions.get(n.id)!;return <g key={n.id} tabIndex={0} role="button" aria-label={`Inspect ${n.type} ${n.label}`} aria-pressed={selected===n.id} onClick={()=>setSelected(n.id)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelected(n.id)}}} className="graphNode"><rect x={p.x-84} y={p.y-32} width="168" height="64" rx="12" fill={selected===n.id?"#742A79":"#24162F"} stroke={selected===n.id?"#E3B8E0":nodeColor(n.type)} strokeWidth={selected===n.id?3:2}/><circle cx={p.x-63} cy={p.y-9} r="7" fill={nodeColor(n.type)}/><text x={p.x-49} y={p.y-5} fontSize="11" fill="#A794B0">{n.type.toUpperCase()}</text><text x={p.x} y={p.y+17} textAnchor="middle" fontSize="12" fontWeight="600" fill="#F4E5F3">{shortName(n)}</text><title>{n.type}: {n.label}</title></g>})}
   </g>
  </svg>
  <p className="muted graphHint">Select a node to inspect properties. Use +/− to zoom; drag the background to pan. Relationships shown are returned by Neo4j, not inferred by the layout.</p>
  {node?<div className="evidenceItem"><div className="incidentTop"><b>{node.type}: {node.type==="Person"?"Person (identity restricted)":node.type==="SourceIP"?"Source IP (restricted)":node.label}</b><button type="button" className="closeIncident" onClick={()=>setSelected(null)}>Close</button></div><dl>{Object.entries(node.properties).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>)}</dl>{(node.type==="Person"||node.type==="SourceIP")&&<p className="muted">Properties are intentionally withheld by the current Presentation API. This does not indicate missing graph data or confirm an identity match. Authorized identity review will require access controls and provenance checks.</p>}</div>:<div className="graphPlaceholder">Select a graph node to view its approved details.</div>}
 </div>;
}
