// SOAR-style review progress per domain (facilitator suggestion during the usability study):
// completed (verdict recorded), in progress (inconclusive) and to do (no verdict), plus groups.
type Row={name:string;done:number;progress:number;todo:number};
export default function ReviewProgress({rows,groups}:{rows:Row[];groups:{reviewed:number;total:number}}){
 const all=rows.reduce((a,r)=>({done:a.done+r.done,progress:a.progress+r.progress,todo:a.todo+r.todo}),{done:0,progress:0,todo:0});
 const bar=(r:{done:number;progress:number;todo:number})=>{
  const total=r.done+r.progress+r.todo;
  if(!total)return <div className="progressTrack"><span className="progressEmpty">No results</span></div>;
  const pct=(n:number)=>`${(n/total)*100}%`;
  return <div className="progressTrack" role="img" aria-label={`${r.done} completed, ${r.progress} in progress, ${r.todo} to do`}>
   {r.done>0&&<span className="progressDone" style={{width:pct(r.done)}}>{r.done}</span>}
   {r.progress>0&&<span className="progressInProgress" style={{width:pct(r.progress)}}>{r.progress}</span>}
   {r.todo>0&&<span className="progressTodo" style={{width:pct(r.todo)}}>{r.todo}</span>}
  </div>;
 };
 return <section className="panel reviewProgress" aria-label="Review progress">
  <h3>Review progress</h3>
  <p className="muted">Human review of detector results in this period. Completed: a verdict is recorded. In progress: marked inconclusive. To do: no verdict yet.</p>
  <div className="progressLegend"><span><i className="progressDone"/>Completed</span><span><i className="progressInProgress"/>In progress</span><span><i className="progressTodo"/>To do</span></div>
  <div className="progressRows">
   <div className="progressRow progressTotal"><span>All results</span>{bar(all)}</div>
   {rows.map(r=><div className="progressRow" key={r.name}><span>{r.name}</span>{bar(r)}</div>)}
   <div className="progressRow"><span>Correlated groups</span>{bar({done:groups.reviewed,progress:0,todo:groups.total-groups.reviewed})}</div>
  </div>
 </section>;
}
