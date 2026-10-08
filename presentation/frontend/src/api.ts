export type Scenario = { name: string; description: string };
export type Decision = { incident_status:string; severity:"LOW"|"MEDIUM"|"HIGH"; response_mode:string; escalation_required:boolean; autonomous_action_allowed:false; decision_rules_triggered:string[]; rationale:string[]; protected_boundaries:Record<string,boolean>; policy_version:string };
export type EvidenceEvent = {event_id:string;domain:string;event_type:string;timestamp:string;state:string;component:string;zone_id:string|null;server_id:string|null;sensor_id:string|null;camera_id:string|null;source_type:string|null};
export type SpecialistAssessment = {specialist_id:string;assessment:string;grounding_status:string;supported_findings:string[];recommended_considerations:string[];limitations:string[];citations:{chunk_id:string;document_id:string}[]};
export type Synthesis = {assessment:string;grounding_status:string;contributing_specialists:string[];supported_cross_domain_findings:string[];recommended_considerations:string[];limitations:string[];citations:{chunk_id:string;document_id:string}[]};
export type Incident = {schema_version:"1.0";scenario_id:string;received_at:string|null;event_time:string|null;scenario_name:string;data_origin:"CONTROLLED_SYNTHETIC_SCENARIO";domains:string[];shared_scope:string|null;shared_entity:string|null;evidence_event_ids:string[];evidence_events:EvidenceEvent[];specialist_assessments:SpecialistAssessment[];synthesis:Synthesis|null;decision:Decision};
let credentials:string|null=null;
export function setCredentials(username:string,password:string){credentials=btoa(unescape(encodeURIComponent(username+":"+password)))}
export function clearCredentials(){credentials=null}
export const getCurrentUser=()=>request<{username:string;roles:string[];zones:string[]}>("/api/v1/auth/me");
async function request<T>(url:string,options?:RequestInit):Promise<T>{const response=await fetch(url,{...options,headers:{"Accept":"application/json",...(credentials?{"Authorization":`Basic ${credentials}`} : {}),...options?.headers}});if(!response.ok)throw new Error(`API request failed (${response.status})`);return response.json() as Promise<T>}
export const getScenarios=()=>request<Scenario[]>("/api/v1/scenarios");
export const runScenario=(name:string)=>request<Incident>(`/api/v1/scenarios/${encodeURIComponent(name)}/run`,{method:"POST"});

export const getIncidents=()=>request<Incident[]>("/api/v1/incidents");

export type GraphNode = {id:string;label:string;type:string;restricted:boolean;properties:Record<string,string|number|boolean>};
export type GraphEdge = {id:string;source:string;target:string;type:string};
export type IncidentGraph = {scenario_id:string;source:"NEO4J_READ_ONLY";nodes:GraphNode[];edges:GraphEdge[]};
export const getIncidentGraph=(id:string)=>request<IncidentGraph>(`/api/v1/incidents/${encodeURIComponent(id)}/graph`);

export type GraphIntegrity = {
 scenario_id:string;
 status:"PASS"|"INCOMPLETE";
 expected_event_count:number;
 observed_event_count:number;
 missing_event_ids:string[];
 missing_ssh_source_relationships:string[];
};
export const getGraphIntegrity=(id:string)=>request<GraphIntegrity>(`/api/v1/incidents/${encodeURIComponent(id)}/graph-integrity`);

export type EvidenceDetail = {event_id:string;domain:string;source_type:string|null;availability:string;details:Record<string,unknown>};
export const getEvidenceDetail=(scenarioId:string,eventId:string)=>request<EvidenceDetail>(`/api/v1/incidents/${encodeURIComponent(scenarioId)}/evidence/${encodeURIComponent(eventId)}`);

export type PPEImageResult = {source_type:string;inference_executed:boolean;pipeline_status:string;image_stored:boolean;observation:PPEObservation|null;image_size:{width:number;height:number};assessment:{overall_status:string;person_count:number;people:Record<string,unknown>[];detections:{class_name:string;confidence:number;bbox_xyxy:number[]}[]}};
export async function validatePPEImage(file:File, retain=false, zone="ZONE-B"):Promise<PPEImageResult>{
 const body=new FormData();body.append("image",file);body.append("retain",String(retain));if(retain)body.append("zone_id",zone);
 return request<PPEImageResult>("/api/v1/ppe/validate-image",{method:"POST",body});
}

export type PPEObservation = {observation_id:string;zone_id:string;created_at:string;status:string;person_count:number;review_status:string;pipeline_status:string;detections?:{class_name:string;confidence:number;bbox_xyxy:number[]}[]};
export type PPEObservationDetail = PPEObservation & {assessment:PPEImageResult["assessment"];image_size:{width:number;height:number}};
export const getPPEObservations=()=>request<PPEObservation[]>("/api/v1/ppe/observations");
export const getPPEObservation=(id:string)=>request<PPEObservationDetail>(`/api/v1/ppe/observations/${encodeURIComponent(id)}`);
export async function getPPEImage(id:string):Promise<Blob>{
 const response=await fetch(`/api/v1/ppe/observations/${encodeURIComponent(id)}/image`,{headers:credentials?{"Authorization":`Basic ${credentials}`}:{}});
 if(!response.ok)throw new Error(`Image unavailable (${response.status})`);
 return response.blob();
}
