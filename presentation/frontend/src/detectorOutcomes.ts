import type {EnvironmentalEvent,FaceObservation,LatestEvidenceReview,MaintenanceEvent,PPEObservation,PublishedSSH} from "./api";

// Abnormal as the Reasoning layer defines it (correlation_rules.ABNORMAL_STATES plus the
// physical-security states; the PPE feed reports NON_COMPLIANT); environment uses the
// detector's own anomaly flag. Display only: never a severity.
export const ABNORMAL=new Set(["EXPLICIT_SECURITY_EVENT","HIGH_CONFIDENCE_ANOMALY","ANOMALY_CANDIDATE","AT_RISK","NON_COMPLIANT","PPE_NON_COMPLIANT","UNKNOWN_PERSON","UNAUTHORIZED"]);
export const DOMAINS=["Cybersecurity","Safety / PPE","Physical Security","Maintenance","Environmental"] as const;
export type Domain=typeof DOMAINS[number];
export type OutcomeKind="ssh"|"ppe"|"face"|"maintenance"|"environment";
export const KIND_DOMAIN:Record<OutcomeKind,Domain>={ssh:"Cybersecurity",ppe:"Safety / PPE",face:"Physical Security",maintenance:"Maintenance",environment:"Environmental"};
// Reasoning-layer domain names used by correlation groups and pairs.
export const DOMAIN_CODE:Record<Domain,string>={"Cybersecurity":"CYBERSECURITY","Safety / PPE":"SAFETY","Physical Security":"PHYSICAL_SECURITY","Maintenance":"MAINTENANCE","Environmental":"ENVIRONMENTAL"};
export type OutcomeRecord={domain:Domain;kind:OutcomeKind;key:string;id:string;zone:string;state:string;time:string;abnormal:boolean;verdict?:LatestEvidenceReview};
export type OutcomeFeeds={ssh:PublishedSSH[];ppe:PPEObservation[];face:FaceObservation[];maintenance:MaintenanceEvent[];environment:EnvironmentalEvent[]};

/** Detector result per published record, with any recorded human verdict beside it (never replacing it). */
export function outcomeRecords(feeds:OutcomeFeeds,verdicts:Record<string,LatestEvidenceReview>):OutcomeRecord[]{
 const make=(kind:OutcomeKind,id:string,zone:string,state:string,time:string,flag?:boolean):OutcomeRecord=>({
  domain:KIND_DOMAIN[kind],kind,key:kind+":"+id,id,zone,state,time,
  abnormal:flag===undefined?ABNORMAL.has(state):flag===true,verdict:verdicts[kind+":"+id]});
 return [
  ...feeds.ssh.map(x=>make("ssh",x.event_id,x.zone_id,x.evidence_state,x.received_at)),
  ...feeds.ppe.map(x=>make("ppe",x.observation_id,x.zone_id,x.status,x.created_at)),
  ...feeds.face.map(x=>make("face",x.observation_id,x.zone_id,x.recognition_status,x.created_at)),
  ...feeds.maintenance.map(x=>make("maintenance",x.event_id,x.zone_id,x.assessment.assessment,x.received_at)),
  ...feeds.environment.map(x=>make("environment",x.event_id,x.zone_id,x.assessment.assessment,x.received_at,x.assessment.anomaly_detected))
 ];
}
