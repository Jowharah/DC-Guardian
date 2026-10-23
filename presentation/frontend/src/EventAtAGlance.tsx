import type {OutcomeRecord} from "./detectorOutcomes";

// Usability study (P01): show a short summary before the detail. Same idea as GroupAtAGlance, for one event.
const words=(s:string)=>s.replaceAll("_"," ").toLowerCase();
export default function EventAtAGlance({record}:{record?:OutcomeRecord}){
 if(!record)return null;
 const v=record.verdict;
 const review=!v?"Not reviewed yet: record a verdict below."
  :v.verdict==="OVERRIDDEN"?`Human override by ${v.reviewer}: ${words(v.corrected_status??"")} (detector said ${words(v.model_status??"")}).`
  :v.verdict==="CONFIRMED"?`Detector result confirmed by ${v.reviewer}.`
  :`Marked inconclusive by ${v.reviewer}: needs another look.`;
 return <section className="atAGlance" aria-label="Event at a glance">
  <h4>At a glance</h4>
  <dl>
   <div><dt>Result</dt><dd><b>{words(record.state)}</b> · {record.domain} · {record.zone}</dd></div>
   <div><dt>What it means</dt><dd>{record.abnormal
    ?<>An <b>abnormal detector result</b>. It comes from an automatic detector and is <b>not yet confirmed by a human</b>.</>
    :<>A normal detector result. No concern was detected.</>}</dd></div>
   <div><dt>Human review</dt><dd className={v?"glanceDone":"glancePending"}>{review}</dd></div>
   <div><dt>Who decides</dt><dd>Severity comes from <b>fixed rules</b>, not AI. AI panels only explain. A human makes the final call.</dd></div>
  </dl>
 </section>;
}
