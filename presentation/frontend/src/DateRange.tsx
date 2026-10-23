// Calendar date range (usability study, P01/P02: "choose which day", not only fixed periods).
// Dates are local calendar days; "to" includes the whole day. Empty means no bound.
export function dayBounds(from:string,to:string){
 const lower=from?new Date(from+"T00:00:00").getTime():-Infinity;
 const upper=to?new Date(to+"T23:59:59.999").getTime():Infinity;
 return {lower,upper};
}
export function inDateRange(time:string|null|undefined,from:string,to:string){
 if(!from&&!to)return true;
 const t=Date.parse(time??"");
 if(!Number.isFinite(t))return false;
 const {lower,upper}=dayBounds(from,to);
 return t>=lower&&t<=upper;
}
export default function DateRangeInputs({from,to,onChange,label="Received",fromText}:{from:string;to:string;onChange:(from:string,to:string)=>void;label?:string;fromText?:string}){
 return <span className="dateRange" role="group" aria-label={`${label} date range`}>
  <label>{fromText??`${label} from`} <input type="date" value={from} max={to||undefined} onChange={e=>onChange(e.target.value,to)}/></label>
  <label>to <input type="date" value={to} min={from||undefined} onChange={e=>onChange(from,e.target.value)}/></label>
  {(from||to)&&<button type="button" className="linkButton" onClick={()=>onChange("","")}>Clear dates</button>}
 </span>;
}
