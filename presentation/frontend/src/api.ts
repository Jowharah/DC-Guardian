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

export type FaceAssessment={recognition_status:"RECOGNIZED"|"UNKNOWN"|"NO_FACE"|"MULTIPLE_FACES";person_id:string;similarity:number|null;distance:number|null;threshold:number;facial_area?:Record<string,number>|null};
export type FaceObservation={observation_id:string;zone_id:string;created_at:string;recognition_status:string;person_id:string;review_status:string;pipeline_status:string};
export type FaceObservationDetail=FaceObservation&{assessment:FaceAssessment};
export type FaceImageResult={assessment:FaceAssessment;observation:FaceObservation|null;image_stored:boolean;authorization_status:string};
export async function validateFaceImage(file:File,retain=false,zone="ZONE-B"):Promise<FaceImageResult>{
 const body=new FormData();body.append("image",file);body.append("retain",String(retain));if(retain)body.append("zone_id",zone);
 return request<FaceImageResult>("/api/v1/face/validate-image",{method:"POST",body});
}
export const getFaceObservations=()=>request<FaceObservation[]>("/api/v1/face/observations");
export const getFaceObservation=(id:string)=>request<FaceObservationDetail>(`/api/v1/face/observations/${encodeURIComponent(id)}`);
export async function getFaceImage(id:string):Promise<Blob>{
 const response=await fetch(`/api/v1/face/observations/${encodeURIComponent(id)}/image`,{headers:credentials?{"Authorization":`Basic ${credentials}`}:{}});
 if(!response.ok)throw new Error(`Face image unavailable (${response.status})`);
 return response.blob();
}

export type FaceZoneAuthorization={status:"AUTHORIZED"|"UNAUTHORIZED"|"UNKNOWN";source:string;reason:string};
export const getFaceAuthorization=(id:string)=>request<FaceZoneAuthorization>(`/api/v1/face/observations/${encodeURIComponent(id)}/authorization`);

export type EmployeeAccess={person_id:string;role:string;authorized_zones:string[]};
export const getEmployees=()=>request<EmployeeAccess[]>("/api/v1/access/employees");
export const registerEmployee=(person_id:string,role:string)=>request<{status:string}>("/api/v1/access/employees",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({person_id,role})});
export const changeEmployeeAccess=(person_id:string,zone_id:string,action:"GRANT"|"REVOKE")=>request<{status:string}>(`/api/v1/access/employees/${encodeURIComponent(person_id)}/zones`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({zone_id,action})});

export type StandaloneEvent={event_id:string;zone_id:string;received_at:string;domain:string;state:string;title:string;asset_id:string;description:string;record_type:"STANDALONE_EVIDENCE";source_type:"OPERATOR_SYNTHETIC";decision_severity:null};
export const getStandaloneEvents=()=>request<StandaloneEvent[]>("/api/v1/events/standalone");
export const createStandaloneEvent=(event:{domain:string;zone_id:string;state:string;title:string;asset_id:string;description:string})=>request<StandaloneEvent>("/api/v1/events/standalone",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(event)});

export const getTopologyOptions=()=>request<{zone_id:string;servers:string[];sensors:string[]}[]>("/api/v1/topology/options");

export type SSHAssessment={source_ip:string|null;window_start:string|null;window_end:string|null;evidence_state:string;detector_votes:number;detector_combination:string;explicit_security_signal:boolean;usernames:string[];evidence:Record<string,unknown>};
export type SSHLogResult={preview_id:string;parsed_count:number;assessment_count:number;security_relevant_count:number;returned_count:number;truncated:boolean;assessments:SSHAssessment[];zone_id:string;server_id:string;retained:false;decision_severity:null};
export async function validateSSHLog(file:File,zone:string,server:string):Promise<SSHLogResult>{
 const body=new FormData();body.append("log",file);body.append("zone_id",zone);body.append("server_id",server);
 return request<SSHLogResult>("/api/v1/ssh/validate-log",{method:"POST",body});
}

export type PublishedSSH=SSHAssessment&{event_id:string;received_at:string;zone_id:string;server_id:string;record_type:"SSH_DETECTOR_EVIDENCE";source_type:string;decision_severity:null;decision_record?:{evaluated_at:string;decision:SSHDecisionResult["decision"];specialist:SSHSpecialistResponse;correlation:SSHCorrelationCheck}|null};
export const getPublishedSSH=()=>request<PublishedSSH[]>("/api/v1/ssh/published");
export const publishSSH=(preview_id:string,indices:number[])=>request<{published_event_ids:string[]}>("/api/v1/ssh/publish",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({preview_id,indices})});

export type SSHReasoningPreview={status:string;pipeline_stage:string;source_ip:string|null;original_timestamp:string|null;zone_id:string;server_id:string;topology_mapping_performed:boolean;correlation_performed:boolean;response_performed:boolean;decision_performed:boolean};
export const previewSSHReasoning=(id:string)=>request<SSHReasoningPreview>(`/api/v1/ssh/published/${encodeURIComponent(id)}/reasoning-preview`);

export type SSHPipelineStage={stage:string;status:string;detail:string};
export type SSHPipelineRun={event_id:string;source_ip:string|null;original_timestamp:string|null;server_id:string;zone_id:string;stages:SSHPipelineStage[];completed_full_pipeline:false;decision_severity:null;note:string};
export const runSSHPipeline=(id:string)=>request<SSHPipelineRun>(`/api/v1/ssh/published/${encodeURIComponent(id)}/run-pipeline`,{method:"POST"});

export type SSHGraphIngestion={status:"INGESTED";graph_event_id:string;scenario_id:string;source_ip:string;server_id:string;zone_id:string;original_timestamp:string;correlation_performed:false;response_performed:false;decision_performed:false;decision_severity:null};
export const ingestSSHGraph=(id:string)=>request<SSHGraphIngestion>(`/api/v1/ssh/published/${encodeURIComponent(id)}/ingest-graph`,{method:"POST"});

export type SSHCorrelationCheck={status:"CORRELATED"|"NO_CORRELATION";correlation_count:number;scenario_id:string;graph_event_id:string;scope:string;note:string};
export const checkSSHCorrelation=(id:string)=>request<SSHCorrelationCheck>(`/api/v1/ssh/published/${encodeURIComponent(id)}/check-correlation`,{method:"POST"});

export type SSHSpecialistResponse={specialist_id:string;assessment:string;grounding_status:string;supported_findings:string[];recommended_considerations:string[];limitations:string[];citations:{chunk_id:string;document_id:string}[];source:string;decision_severity:null;confirmed_compromise:false};
export const getSSHSpecialistResponse=(id:string)=>request<SSHSpecialistResponse>(`/api/v1/ssh/published/${encodeURIComponent(id)}/specialist-response`,{method:"POST"});

export type SSHDecisionResult={event_id:string;zone_id:string;server_id:string;source_ip:string;evidence_state:string;correlation:SSHCorrelationCheck;specialist:SSHSpecialistResponse;decision:{severity:"LOW"|"MEDIUM"|"HIGH";incident_status:string;response_mode:string;autonomous_action_allowed:false;escalation_required:boolean;decision_rules_triggered:string[];policy_version:string};record_type:"STANDALONE_SSH_DECISION";incident_linked:false;decision_source:string;note:string};
export const evaluateSSHDecision=(id:string)=>request<SSHDecisionResult>(`/api/v1/ssh/published/${encodeURIComponent(id)}/decision`,{method:"POST"});

export const getSavedSSHDecision=(id:string)=>request<{evaluated_at:string;decision:SSHDecisionResult["decision"];specialist:SSHSpecialistResponse;correlation:SSHCorrelationCheck}>(`/api/v1/ssh/published/${encodeURIComponent(id)}/decision`);
