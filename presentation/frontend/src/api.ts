export type Scenario = { name: string; description: string };
export type Decision = { incident_status:string; severity:"LOW"|"MEDIUM"|"HIGH"; response_mode:string; escalation_required:boolean; autonomous_action_allowed:false; decision_rules_triggered:string[]; rationale:string[]; protected_boundaries:Record<string,boolean>; policy_version:string };
export type EvidenceEvent = {event_id:string;domain:string;event_type:string;timestamp:string;state:string;component:string;zone_id:string|null;server_id:string|null;sensor_id:string|null;camera_id:string|null;source_type:string|null};
export type Incident = {schema_version:"1.0";scenario_id:string;received_at:string|null;event_time:string|null;scenario_name:string;data_origin:"CONTROLLED_SYNTHETIC_SCENARIO";domains:string[];shared_scope:string|null;shared_entity:string|null;evidence_event_ids:string[];evidence_events:EvidenceEvent[];decision:Decision};
async function request<T>(url:string,options?:RequestInit):Promise<T>{const response=await fetch(url,{...options,headers:{"Accept":"application/json",...options?.headers}});if(!response.ok)throw new Error(`API request failed (${response.status})`);return response.json() as Promise<T>}
export const getScenarios=()=>request<Scenario[]>("/api/v1/scenarios");
export const runScenario=(name:string)=>request<Incident>(`/api/v1/scenarios/${encodeURIComponent(name)}/run`,{method:"POST"});

export const getIncidents=()=>request<Incident[]>("/api/v1/incidents");

export type GraphNode = {id:string;label:string;type:string;properties:Record<string,string|number|boolean>};
export type GraphEdge = {id:string;source:string;target:string;type:string};
export type IncidentGraph = {scenario_id:string;source:"NEO4J_READ_ONLY";nodes:GraphNode[];edges:GraphEdge[]};
export const getIncidentGraph=(id:string)=>request<IncidentGraph>(`/api/v1/incidents/${encodeURIComponent(id)}/graph`);
