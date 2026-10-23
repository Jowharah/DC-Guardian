import type {UnifiedCorrelationGroup} from "./api";

// Usability study (2026-10-21/22): participants missed that grouping is not proof of cause and that
// severity comes from fixed rules. This box states both first, before the detail.
export const DOMAIN_LABELS:Record<string,string>={CYBERSECURITY:"Cybersecurity",PHYSICAL_SECURITY:"Physical security",
 SAFETY:"Safety / PPE",MAINTENANCE:"Maintenance",ENVIRONMENTAL:"Environmental"};
export const domainLabel=(domain:string)=>DOMAIN_LABELS[domain]??domain.replaceAll("_"," ").toLowerCase();

export default function GroupAtAGlance({group}:{group:UnifiedCorrelationGroup}){
 const members=group.members??[];
 const reviewed=members.filter(m=>m.human_review).length;
 const spread=group.linkage?.time_spread_minutes;
 return <section className="atAGlance" aria-label="Group at a glance">
  <h4>At a glance</h4>
  <dl>
   <div><dt>Why grouped</dt><dd>{group.evidence.length} events in <b>{group.zone_id}</b>{spread!==undefined&&spread!==null?<>, {spread} min apart</>:null}, linked by {group.edges.length} shared-context link{group.edges.length===1?"":"s"} (same zone and time window).</dd></div>
   <div><dt>Domains</dt><dd className="domainTags">{group.domains.map(d=><span key={d} className={`domainTag domain-${d.toLowerCase()}`}>{domainLabel(d)}</span>)}</dd></div>
   <div><dt>What it does not show</dt><dd><b>Not proof of cause.</b> Being grouped does not mean one event caused another, or that the same person was involved.</dd></div>
   <div><dt>Severity</dt><dd>{group.decision_severity?<><span className={`severity severity-${group.decision_severity.toLowerCase()}`}>{group.decision_severity}</span> set by <b>fixed rules</b> ({group.severity_policy??"DCG-DECISION-v2"}), <b>not by AI</b>.{group.escalated?" Raised one level because the events form a known linking mechanism.":""}</>:"No rule-based severity."}</dd></div>
   <div><dt>Human review</dt><dd>Required before any action. {reviewed} of {members.length} events have a human verdict; the group's review state is under <a href="#investigationState">Investigation state</a>.</dd></div>
  </dl>
 </section>;
}
