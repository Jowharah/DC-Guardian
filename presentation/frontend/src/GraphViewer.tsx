import {useEffect,useMemo,useState} from "react";
import {getIncidentGraph,getOperationalGraph,getStandaloneGraph,getPhysicalImageGraph,getUnifiedGraph,type IncidentGraph,type GraphNode} from "./api";

const palette:Record<string,string>={Event:"#742A79",Camera:"#524184",Person:"#794F65",Server:"#8392CF",Zone:"#A794B0",Sensor:"#6D83B6",Asset:"#7566AB",SourceIP:"#794F65"};
const width=960,height=560;
function nodeColor(type:string){return palette[type]??"#524184"}
function shortName(n:GraphNode){if(n.type==="Event"){const t=String(n.properties.event_type??"");if(t.includes("PPE"))return "PPE Assessment";if(t.includes("FACE"))return "Face Identification";if(t.includes("SSH"))return "SSH Assessment";if(t.includes("ENVIRONMENT"))return "Environmental Event";if(t.includes("STORAGE"))return "Maintenance Event";return "Evidence Event"}if(n.restricted)return n.type==="SourceIP"?"Source IP (restricted)":"Person (restricted)";const v=n.label;return v.length>23?v.slice(0,20)+"…":v}
export default function GraphViewer({scenarioId,operational=false,standalone,physical=false,unified=false}:{scenarioId:string;operational?:boolean;physical?:boolean;unified?:boolean;standalone?:"ssh"|"maintenance"|"environment"}){
 const [graph,setGraph]=useState<IncidentGraph|null>(null);
 const [selected,setSelected]=useState<string|null>(null);
 const [error,setError]=useState("");
 const [zoom,setZoom]=useState(1);
 const [offset,setOffset]=useState({x:0,y:0});
 const [drag,setDrag]=useState<{x:number;y:number;ox:number;oy:number}|null>(null);
 useEffect(()=>{let active=true;setGraph(null);setSelected(null);setError("");setZoom(1);setOffset({x:0,y:0});(unified?getUnifiedGraph(scenarioId):physical?getPhysicalImageGraph(scenarioId):standalone?getStandaloneGraph(standalone,scenarioId):operational?getOperationalGraph(scenarioId):getIncidentGraph(scenarioId)).then(data=>{if(active)setGraph(data)}).catch((err)=>{if(active)setError(operational?`Operational graph request failed: ${err instanceof Error?err.message:"Unknown error"}. Check the API response and backend logs.`:"Neo4j graph unavailable. Verify database connectivity.")});return()=>{active=false}},[scenarioId,operational,standalone,physical,unified]);
 const shown=useMemo(()=>graph?.nodes.slice(0,40)??[],[graph]);
 const layout=useMemo(()=>{
   const m=new Map<string,{x:number;y:number}>();
   if(!graph||!shown.length)return {m,W:width,H:height};
   const order=["Zone","Rack","Sensor","Camera","Equipment","Server","Asset","Person","SourceIP","Event"];
   const rank=(t:string)=>{const r=order.indexOf(t);return r<0?order.length:r};
   // Usability study: the graph was unclear. Lay nodes out in layers by hop distance from the zone
   // (zone, then what sits in it, then the next hop ...), so relationships run between neighbouring
   // columns and their labels do not collide. Nodes not connected to the zone follow, by type.
   const ids=new Set(shown.map(n=>n.id));
   const near=new Map<string,string[]>();
   for(const e of graph.edges){if(!ids.has(e.source)||!ids.has(e.target))continue;
    near.set(e.source,[...(near.get(e.source)??[]),e.target]);near.set(e.target,[...(near.get(e.target)??[]),e.source])}
   const depth=new Map<string,number>();
   const zones=shown.filter(n=>n.type==="Zone");
   zones.forEach(z=>depth.set(z.id,0));
   const queue=zones.map(z=>z.id);
   while(queue.length){const id=queue.shift()!;for(const next of near.get(id)??[])if(!depth.has(next)){depth.set(next,depth.get(id)!+1);queue.push(next)}}
   const deepest=Math.max(0,...depth.values());
   const unlinked=[...new Set(shown.filter(n=>!depth.has(n.id)).map(n=>n.type))].sort((a,b)=>rank(a)-rank(b));
   const layerOf=(n:GraphNode)=>depth.has(n.id)?depth.get(n.id)!:(zones.length?deepest+1:0)+unlinked.indexOf(n.type);
   const layers=new Map<number,GraphNode[]>();
   shown.forEach(n=>{const l=layerOf(n);layers.set(l,[...(layers.get(l)??[]),n])});
   const columns=[...layers.keys()].sort((a,b)=>a-b);
   // 270 px between columns: a 168 px node plus room for a relationship label between neighbours.
   // The canvas widens (and scrolls sideways if needed) rather than shrinking nodes or labels.
   const W=Math.max(width,190+(columns.length-1)*270);
   const H=Math.max(height,...columns.map(c=>(layers.get(c)!.length+1)*90));
   columns.forEach((c,i)=>{const nodes=layers.get(c)!.sort((a,b)=>rank(a.type)-rank(b.type)||a.label.localeCompare(b.label));
    nodes.forEach((n,j)=>m.set(n.id,{x:columns.length===1?W/2:95+i*(W-190)/(columns.length-1),y:H*(j+1)/(nodes.length+1)}))});
   return {m,W,H};
 },[graph,shown]);
 const positions=layout.m;
 const node=shown.find(n=>n.id===selected);
 const visibleIds=new Set(shown.map(n=>n.id));
 const edges=(graph?.edges??[]).filter(e=>visibleIds.has(e.source)&&visibleIds.has(e.target));
 // Relationship labels at edge midpoints, nudged down when two would overlap (crossing edges).
 const labelSpots:{e:typeof edges[number];x:number;y:number}[]=[];
 for(const e of edges){const a=positions.get(e.source)!,b=positions.get(e.target)!;const x=(a.x+b.x)/2;let y=(a.y+b.y)/2;
  const w=Math.max(68,e.type.length*7+18);
  for(let tries=0;tries<6&&labelSpots.some(o=>Math.abs(o.x-x)<(w+Math.max(68,o.e.type.length*7+18))/2&&Math.abs(o.y-y)<28);tries++)y+=30;
  labelSpots.push({e,x,y})}
 const reset=()=>{setZoom(1);setOffset({x:0,y:0})};
 if(error)return <div className="panel muted" role="status">{error}</div>;
 if(!graph)return <div className="panel muted">Loading graph…</div>;
 if(!shown.length)return <div className="panel muted">No graph nodes found for this scenario.</div>;
 return <div className="panel graphPanel">
  <div className="graphToolbar"><div><b>Infrastructure relationships</b><p className="muted">{graph.nodes.length} nodes · {graph.edges.length} relationships · Neo4j read-only</p></div><div className="graphControls"><button type="button" onClick={()=>setZoom(z=>Math.min(2.5,+(z+.2).toFixed(2)))} aria-label="Zoom in">+</button><button type="button" onClick={()=>setZoom(z=>Math.max(.5,+(z-.2).toFixed(2)))} aria-label="Zoom out">−</button><button type="button" onClick={reset}>Reset</button></div></div>
  <div className="graphLegend">{[...new Set(shown.map(n=>n.type))].map(t=><span key={t}><i style={{background:nodeColor(t)}}/>{t}</span>)}{shown.some(n=>n.type==="Zone")&&<span className="graphZoneNote">Highlighted in amber: the zone where these events were placed</span>}</div>
  <div className="graphScroll"><svg className="graphCanvas" style={{minWidth:`${Math.round(layout.W*0.85)}px`}} viewBox={`0 0 ${layout.W} ${layout.H}`} role="group" aria-label="Interactive Neo4j scenario infrastructure graph" onPointerDown={e=>{if(e.target===e.currentTarget){e.currentTarget.setPointerCapture(e.pointerId);setDrag({x:e.clientX,y:e.clientY,ox:offset.x,oy:offset.y})}}} onPointerMove={e=>{if(drag){const bounds=e.currentTarget.getBoundingClientRect();setOffset({x:drag.ox+(e.clientX-drag.x)*width/bounds.width,y:drag.oy+(e.clientY-drag.y)*height/bounds.height})}}} onPointerUp={()=>setDrag(null)} onPointerCancel={()=>setDrag(null)}>
   <defs><marker id="dcg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="#8392CF"/></marker></defs>
   <g transform={`translate(${offset.x} ${offset.y}) translate(${layout.W/2} ${layout.H/2}) scale(${zoom}) translate(${-layout.W/2} ${-layout.H/2})`}>
    {edges.map(e=>{const a=positions.get(e.source)!,b=positions.get(e.target)!;const dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy)||1;const ex=Math.min(Math.abs(dx)/len*84+Math.abs(dy)/len*32,len/2-4),x1=a.x+dx*ex/len,y1=a.y+dy*ex/len,x2=b.x-dx*(ex+6)/len,y2=b.y-dy*(ex+6)/len;return <line key={e.id} x1={x1} y1={y1} x2={x2} y2={y2} stroke="#8392CF" strokeWidth="2" opacity=".8" markerEnd="url(#dcg-arrow)"/>})}{shown.map(n=>{const p=positions.get(n.id)!;return <g key={n.id} tabIndex={0} role="button" aria-label={`Inspect ${n.type} ${n.label}`} aria-pressed={selected===n.id} onClick={()=>setSelected(n.id)} onKeyDown={e=>{if(e.key==="Enter"||e.key===" "){e.preventDefault();setSelected(n.id)}}} className="graphNode"><rect x={p.x-84} y={p.y-32} width="168" height="64" rx="12" fill={selected===n.id?"#742A79":n.type==="Zone"?"#3A2B12":"#24162F"} stroke={selected===n.id?"#E3B8E0":n.type==="Zone"?"#F2B84B":nodeColor(n.type)} strokeWidth={selected===n.id||n.type==="Zone"?3:2}/><circle cx={p.x-63} cy={p.y-9} r="7" fill={nodeColor(n.type)}/><text x={p.x-49} y={p.y-5} fontSize="11" fill="#A794B0">{n.type.toUpperCase()}</text><text x={p.x} y={p.y+17} textAnchor="middle" fontSize="12" fontWeight="600" fill="#F4E5F3">{shortName(n)}</text><title>{n.type}: {n.label}</title></g>})}{labelSpots.map(({e,x,y})=>{return <g key={"label:"+e.id} className="graphEdgeLabel" transform={`translate(${x} ${y})`}><rect x={-Math.max(34,e.type.length*3.5+9)} y="-13" width={Math.max(68,e.type.length*7+18)} height="25" rx="8" fill="#160C20" stroke="#8392CF"/><text fill="#E3B8E0" fontSize="12" textAnchor="middle" y="4">{e.type}</text></g>})}
   </g>
  </svg></div>
  <p className="muted graphHint">Select a node to inspect properties. Use +/− to zoom; drag the background to pan. Relationships shown are returned by Neo4j, not inferred by the layout.</p>
  {node?<div className="evidenceItem"><div className="incidentTop"><b>{node.type}: {node.restricted?(node.type==="Person"?"Person (identity restricted)":"Source IP (restricted)"):node.label}</b><button type="button" className="closeIncident" onClick={()=>setSelected(null)}>Close</button></div><dl>{Object.entries(node.properties).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{String(v)}</dd></div>)}</dl>{node.restricted&&<p className="muted">Properties are intentionally withheld by the current Presentation API. This does not indicate missing graph data or confirm an identity match. Authorized identity review will require access controls and provenance checks.</p>}</div>:<div className="graphPlaceholder">Select a graph node to view its approved details.</div>}
 </div>;
}
