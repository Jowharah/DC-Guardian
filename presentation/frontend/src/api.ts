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

export type PPEImageResult = {source_type:string;inference_executed:boolean;pipeline_status:string;image_stored:boolean;observation:PPEObservation|null;image_size:{width:number;height:number};assessment:{overall_status:string;person_count:number;people:{person_index:number;status:string;required_ppe_detected:string[];required_ppe_not_detected:string[];required_ppe:string[]}[];detections:{class_name:string;confidence:number;bbox_xyxy:number[]}[]}};
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

export type MaintenanceAssessment={domain:"MAINTENANCE";assessment:"NORMAL"|"AT_RISK";serial_number:string;observation_timestamp:string;failure_probability:number;operating_threshold:number;failure_horizon_days:number;model_name:string;evidence:Record<string,number|null>};
export type MaintenanceWorkflow={stages:{stage:string;status:string;detail:string}[];correlation:{status:string;count:number;scope:string};specialist:{assessment:string;grounding_status:string;supported_findings:string[];recommended_considerations:string[];limitations:string[];citations:{chunk_id:string;document_id:string}[]}|null;decision:null;graph_event_id:string};
export type MaintenanceEvent={event_id:string;received_at:string;zone_id:string;server_id:string;assessment:MaintenanceAssessment;history:{date:string;[key:string]:string|number}[];workflow:MaintenanceWorkflow;record_type:"MAINTENANCE_EVIDENCE";decision_severity:null};
export type MaintenanceValidation={event_id:string;assessment:MaintenanceAssessment;history:MaintenanceEvent["history"];workflow:MaintenanceWorkflow|null;published:boolean;zone_id:string;server_id:string;decision_severity:null};
export const getMaintenanceEvents=()=>request<MaintenanceEvent[]>("/api/v1/maintenance/events");
export function validateMaintenance(file:File,zone_id:string,server_id:string,publish:boolean){
 const body=new FormData();body.append("file",file);body.append("zone_id",zone_id);body.append("server_id",server_id);body.append("publish",String(publish));
 return request<MaintenanceValidation>("/api/v1/maintenance/validate",{method:"POST",body});
}

export type SSHProcessedEvent={event_id:string;assessment_index:number;status:string;graph_event_id?:string;correlation?:SSHCorrelationCheck;decision?:SSHDecisionResult["decision"];specialist?:SSHSpecialistResponse;stages:{stage:string;status:string;detail?:string}[]};
export type SSHProcessResult=SSHLogResult&{published:boolean;events:SSHProcessedEvent[]};
export function processSSHLog(file:File,zone:string,server:string,publish:boolean){
 const body=new FormData();body.append("log",file);body.append("zone_id",zone);body.append("server_id",server);body.append("publish",String(publish));
 return request<SSHProcessResult>("/api/v1/ssh/process-log",{method:"POST",body});
}

export type EnvironmentalAssessment={assessment:string;observation_timestamp:string;measurements:{temperature_c:number|null;humidity_pct:number|null};anomaly_detected:boolean;evidence:{thresholds:Record<string,number>;triggered_conditions:string[]}};
export type EnvironmentalEvent={event_id:string;received_at:string;zone_id:string;sensor_id:string;assessment:EnvironmentalAssessment;history:{timestamp:string;temperature_c:number|null;humidity_pct:number|null}[];workflow:{stages:{stage:string;status:string;detail?:string}[];correlation:{status:string;scope:string};specialist:SpecialistAssessment|null;reading_states?:string[];decision:null};evidence_event_ids?:string[];record_type:"ENVIRONMENTAL_EVIDENCE";decision_severity:null};
export const getEnvironmentalEvents=()=>request<EnvironmentalEvent[]>("/api/v1/environment/events");
export function validateEnvironment(file:File,zone:string,sensor:string,publish:boolean){
 const body=new FormData();body.append("file",file);body.append("zone_id",zone);body.append("sensor_id",sensor);body.append("publish",String(publish));
 return request<{published:boolean;assessments:EnvironmentalAssessment[];events:{event_id:string;assessment:EnvironmentalAssessment;workflow:EnvironmentalEvent["workflow"]}[]}>("/api/v1/environment/validate",{method:"POST",body});
}

export type OperationalCorrelation={id:string;zone_id:string;maintenance_event_id:string;environment_event_id:string;maintenance:MaintenanceEvent;environment:EnvironmentalEvent;time_difference_seconds:number;matched_environment_timestamp:string;correlation_type:string;scope:"ZONE";status:"CORRELATION_CANDIDATE"|"DECISION_COMPLETE";decision:Decision|null;decision_severity:"LOW"|"MEDIUM"|"HIGH"|null;explanation:string};
export const getOperationalCorrelations=()=>request<OperationalCorrelation[]>("/api/v1/operations/correlations");

export const getOperationalGraph=(id:string)=>request<IncidentGraph>(`/api/v1/operations/correlations/${encodeURIComponent(id)}/graph`);

export type OperationalDecisionResult={candidate_id:string;evaluated_at:string;specialist:SpecialistAssessment;decision:Decision;evidence_event_ids:string[]};
export const getOperationalDecision=(id:string)=>request<OperationalDecisionResult>(`/api/v1/operations/correlations/${encodeURIComponent(id)}/decision`);
export const evaluateOperationalDecision=(id:string)=>request<OperationalDecisionResult>(`/api/v1/operations/correlations/${encodeURIComponent(id)}/decision`,{method:"POST"});

export const getStandaloneGraph=(kind:"ssh"|"maintenance"|"environment",id:string)=>request<IncidentGraph>(`/api/v1/evidence/${kind}/${encodeURIComponent(id)}/graph`);

export type ImageCaptureMetadata={capture_metadata:{camera_id:string;zone_id:string;captured_at:string;provenance:string}|null;graph_projection:{event_id:string;graph_status:string;provenance_status:string;correlation_status:string;decision_status:string}|null};
export const getImageCaptureMetadata=(kind:"ppe"|"face",id:string)=>request<ImageCaptureMetadata>(`/api/v1/image-observations/${kind}/${encodeURIComponent(id)}/metadata`);

export type PhysicalImageCandidate={id:string;zone_id:string;ppe_observation_id:string;face_observation_id:string;camera_id:string;captured_at:string;ppe_status:string;face_status:string;source_match:string;provenance:string;time_difference_seconds:number;receipt_difference_seconds:number;ppe_received_at:string;face_received_at:string;correlation_status:string;decision_severity:null;explanation:string};
export const getPhysicalImageCandidates=()=>request<PhysicalImageCandidate[]>("/api/v1/physical/image-correlations");

export const getPhysicalImageGraph=(id:string)=>request<IncidentGraph>(`/api/v1/physical/image-correlations/${encodeURIComponent(id)}/graph`);

export type PhysicalSpecialistResult={evaluated_at:string;specialist:SpecialistAssessment;evidence_event_ids:string[];decision:null};
export const getPhysicalSpecialist=(id:string)=>request<PhysicalSpecialistResult>(`/api/v1/physical/image-correlations/${encodeURIComponent(id)}/specialist`);
export const evaluatePhysicalSpecialist=(id:string)=>request<PhysicalSpecialistResult>(`/api/v1/physical/image-correlations/${encodeURIComponent(id)}/specialist`,{method:"POST"});

export type PhysicalPersonAssociation={candidate_id:string;recognized_person_id:string|null;status:"MATCH_CANDIDATE"|"AMBIGUOUS"|"NO_MATCH"|"NOT_EVALUATED";person_index:number|null;ppe_status:string|null;identity_link_established:false;decision_severity:null;reason:string;face_containment_ratio?:number};
export const getPhysicalPersonAssociation=(id:string)=>request<PhysicalPersonAssociation>(`/api/v1/physical/image-correlations/${encodeURIComponent(id)}/person-association`);

export type PhysicalReviewResult={candidate_id:string;specialist_evaluated_at:string;decision:{policy_version:string;status:string;severity:null;response_mode:string;autonomous_action_allowed:false;reasons:string[];identity_link_established:false;confirmed_ppe_violation:false;decision_v1_severity_evaluated:false}};
export const getPhysicalReview=(id:string)=>request<PhysicalReviewResult>(`/api/v1/physical/image-correlations/${encodeURIComponent(id)}/review-decision`);

export type FaceSSHCandidate={id:string;zone_id:string;face_observation_id:string;ssh_event_id:string;camera_id:string;server_id:string;face_capture_time:string;ssh_original_time:string;ssh_context_time:string;ssh_time_provenance:string;time_difference_seconds:number;face_recognition_status:string;ssh_evidence_state:string;status:"CONTROLLED_CANDIDATE";decision_severity:null;explanation:string};
export const getFaceSSHCandidates=()=>request<FaceSSHCandidate[]>("/api/v1/cyber/face-ssh/candidates");

export type UnifiedCorrelationGroup={id:string;zone_id:string;domains:string[];evidence:{kind:string;domain:string;observation_id:string}[];edges:{type:string;left:[string,string];right:[string,string];source_id:string;zone_id:string;details:Record<string,string|number>}[];source_candidate_ids:string[];status:"CORRELATION_GROUP_CANDIDATE";decision:null;decision_severity:null;autonomous_action_allowed:false;identity_link_established:false;causal_relationship_established:false;note:string};
export const getUnifiedCorrelations=()=>request<UnifiedCorrelationGroup[]>("/api/v1/correlations/unified");

export const getUnifiedGraph=(id:string)=>request<IncidentGraph>(`/api/v1/correlations/unified/${encodeURIComponent(id)}/graph`);

export type UnifiedSpecialistResult={group_id:string;evaluated_at:string;specialists:Record<string,SpecialistAssessment>;decision:null;decision_severity:null};
export const getUnifiedSpecialists=(id:string)=>request<UnifiedSpecialistResult>(`/api/v1/correlations/unified/${encodeURIComponent(id)}/specialists`);
export const evaluateUnifiedSpecialists=(id:string)=>request<UnifiedSpecialistResult>(`/api/v1/correlations/unified/${encodeURIComponent(id)}/specialists`,{method:"POST"});

export type UnifiedSynthesisResult={group_id:string;specialists_evaluated_at:string;synthesis:{grounding_status:string;contributing_specialists:string[];supported_source_findings:{specialist:string;finding:string}[];source_limitations:{specialist:string;limitation:string}[];validated_contextual_links:{type:string;source_id:string}[];assessment:string;decision_status:"NOT_RUN";decision_severity:null;autonomous_action_allowed:false}};
export const getUnifiedSynthesis=(id:string)=>request<UnifiedSynthesisResult>(`/api/v1/correlations/unified/${encodeURIComponent(id)}/synthesis`);

export type UnifiedReviewDecision={group_id:string;specialists_evaluated_at:string;decision:{policy_version:string;status:string;response_mode:string;review_reasons:string[];severity:null;autonomous_action_allowed:false;note:string}};
export const getUnifiedReviewDecision=(id:string)=>request<UnifiedReviewDecision>(`/api/v1/correlations/unified/${encodeURIComponent(id)}/review-decision`);

export type PublishedCorrelationCheck={kind:string;observation_ids:string[];status:"CANDIDATES_FOUND"|"NO_ELIGIBLE_CORRELATION";groups:UnifiedCorrelationGroup[];checked_against:string;note:string};
export const checkPublishedCorrelations=(kind:string,observation_ids:string[])=>request<PublishedCorrelationCheck>("/api/v1/correlations/check-published",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind,observation_ids})});

export type ControlledSSHTimeResult={event_id:string;observed_at:string;provenance:string;original_detector_timestamp_unchanged:boolean;verified_observation_time:boolean};
export const declareControlledSSHTime=(eventId:string,observedAt:string)=>request<ControlledSSHTimeResult>(`/api/v1/ssh/published/${encodeURIComponent(eventId)}/controlled-time`,{method:"PUT",headers:{"Content-Type":"application/json"},body:JSON.stringify({observed_at:observedAt,acknowledgment:true})});

export const declareImageCapture=(kind:"ppe"|"face",id:string,camera_id:string,captured_at:string)=>request<{observation_id:string;capture_metadata:{camera_id:string;captured_at:string;zone_id:string;provenance:string};graph_projection:{graph_status:string}}>(`/api/v1/images/${kind}/${encodeURIComponent(id)}/capture-declaration`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({camera_id,captured_at,acknowledgment:true})});

export const getCameraTopology=()=>request<{zone_id:string;cameras:string[]}[]>("/api/v1/topology/cameras");

export type FaceSSHSpecialistReview={candidate_id:string;evaluated_at:string;specialists:Record<string,SpecialistAssessment>;authorization:{status:string;source:string;reason:string};review:{status:string;response_mode:string;reasons:string[];severity:null;identity_to_ssh_established:false;physical_presence_verified:false;autonomous_action_allowed:false}};
export const evaluateFaceSSHSpecialists=(id:string)=>request<FaceSSHSpecialistReview>(`/api/v1/cyber/face-ssh/candidates/${encodeURIComponent(id)}/specialists`,{method:"POST"});

export const getSavedFaceSSHSpecialists=(id:string)=>request<FaceSSHSpecialistReview>(`/api/v1/cyber/face-ssh/candidates/${encodeURIComponent(id)}/specialists`);

export type HumanReviewRecord={audit_id:string;group_id:string;zone_id:string;reviewer:string;recorded_at:string;outcome:"REVIEWED_NO_FINDING"|"NEEDS_FOLLOW_UP"|"INCONCLUSIVE";rationale:string;evidence_signature:string;policy_version:string;review_status:string;previous_hash:string;entry_hash:string};
export const getUnifiedHumanReviews=(id:string)=>request<{group_id:string;zone_id:string;records:HumanReviewRecord[];note:string}>(`/api/v1/reviews/unified/${encodeURIComponent(id)}/records`);
export const submitUnifiedHumanReview=(id:string,outcome:HumanReviewRecord["outcome"],rationale:string)=>request<HumanReviewRecord>(`/api/v1/reviews/unified/${encodeURIComponent(id)}/records`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({outcome,rationale,acknowledgment:true})});

export type AuditIntegrityResult={
 status:"PASS"|"FAILED";checked:number;head_hash?:string;
 reason?:string;audit_id?:string;limitation?:string
};
export const getAuditIntegrity=()=>request<AuditIntegrityResult>("/api/v1/reviews/audit-integrity");

export type InvestigatorAnswer={group_id:string;answer:string;evidence_refs:{kind:string;observation_id:string}[];read_only:true;decision_severity_assigned:false;notice:string;sources?:{kind:string;id:string;role:string}[]};
export const askUnifiedInvestigator=(groupId:string,question:string)=>request<InvestigatorAnswer>(`/api/v1/investigator/unified/${encodeURIComponent(groupId)}/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});

export type InvestigatorHistoryEntry={id:string;created_at:string;question:string;answer:string};
export const getInvestigatorHistory=(id:string)=>request<{group_id:string;messages:InvestigatorHistoryEntry[]}>(`/api/v1/investigator/unified/${encodeURIComponent(id)}/history`);
export const saveInvestigatorHistory=(id:string,question:string,answer:string)=>request<InvestigatorHistoryEntry>(`/api/v1/investigator/unified/${encodeURIComponent(id)}/history`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,answer})});
export const clearInvestigatorHistory=(id:string)=>request<{cleared:boolean}>(`/api/v1/investigator/unified/${encodeURIComponent(id)}/history`,{method:"DELETE"});

export const askOperationalInvestigator=(candidateId:string,question:string)=>request<{candidate_id:string;answer:string;read_only:boolean;sources?:{kind:string;id:string;role:string}[]}>(`/api/v1/investigator/operations/${encodeURIComponent(candidateId)}/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});

export type InvestigatorSingleKind="ssh"|"ppe"|"face"|"maintenance"|"environment";
export const askSingleEvidenceInvestigator=(kind:InvestigatorSingleKind,evidenceId:string,question:string)=>request<{kind:string;evidence_id:string;answer:string;read_only:boolean;sources?:{kind:string;id:string;role:string}[]}>(`/api/v1/investigator/evidence/${encodeURIComponent(kind)}/${encodeURIComponent(evidenceId)}/ask`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question})});

export type InvestigatorScope="unified"|"operations"|"single";
export function investigatorHistoryPath(scope:InvestigatorScope,id:string,kind?:InvestigatorSingleKind):string{
 if(scope==="unified")return `/api/v1/investigator/unified/${encodeURIComponent(id)}/history`;
 if(scope==="operations")return `/api/v1/investigator/operations/${encodeURIComponent(id)}/history`;
 if(!kind)throw new Error("Single Evidence kind is required");
 return `/api/v1/investigator/evidence/${encodeURIComponent(kind)}/${encodeURIComponent(id)}/history`;
}
export const getScopedInvestigatorHistory=(scope:InvestigatorScope,id:string,kind?:InvestigatorSingleKind)=>request<{messages:InvestigatorHistoryEntry[]}>(investigatorHistoryPath(scope,id,kind));
export const saveScopedInvestigatorHistory=(scope:InvestigatorScope,id:string,question:string,answer:string,kind?:InvestigatorSingleKind)=>request<InvestigatorHistoryEntry>(investigatorHistoryPath(scope,id,kind),{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({question,answer})});
export const clearScopedInvestigatorHistory=(scope:InvestigatorScope,id:string,kind?:InvestigatorSingleKind)=>request<{cleared:boolean}>(investigatorHistoryPath(scope,id,kind),{method:"DELETE"});
