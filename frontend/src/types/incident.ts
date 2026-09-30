export type Evidence = {
  id: string;
  incident_id: string;
  code: string;
  evidence_type: string;
  state: string;
  value_numeric: number | null;
  value_text: string | null;
  unit: string | null;
  source: string;
  observed_at: string;
  reliability_score: number;
  provenance: Record<string, unknown>;
  is_simulated: boolean;
};

export type Decision = {
  id: string;
  incident_id: string;
  question: string;
  deadline: string;
  status: string;
  current_version: number;
};

export type Incident = {
  id: string;
  title: string;
  description: string;
  incident_type: string;
  location_name: string;
  latitude: number | null;
  longitude: number | null;
  severity: string;
  status: string;
  occurred_at: string;
  created_at: string;
  updated_at: string;
  evidence: Evidence[];
  decisions: Decision[];
};

export type DecisionVersion = {
  id: string;
  decision_id: string;
  version_number: number;
  summary: string;
  uncertainty_level: string;
  evidence_snapshot: {
    evidence_ids: string[];
    evidence_codes?: string[];
    triggering_evidence_id?: string;
    uncertainty_score?: number;
    hypothesis_updates?: Array<Record<string, unknown>>;
  };
  approval_status: string;
  created_by: string;
  approved_by: string | null;
  created_at: string;
};

export type DecisionDetail = Decision & {
  versions: DecisionVersion[];
};

export type IncidentListItem = Omit<Incident, "evidence" | "decisions"> & {
  evidence_count: number;
  pending_decision_count: number;
};

export type RankingResult = {
  evidence_id: string;
  candidate_name: string;
  score: number;
  rank: number;
  decision_value: number;
  reliability: number;
  feasibility: number;
  cost: number;
  time: number;
  explanation: string;
  strengths: string[];
  tradeoffs: string[];
  selected: boolean;
};

export type CandidateProfile = {
  incident_type: string;
  evidence_id: string;
  evidence_code: string;
  candidate_name: string;
  target_hypotheses: string[];
  related_evidence_codes: string[];
  relationship: string;
  confidence: number;
  decision_value: number;
  reliability: number;
  feasibility: number;
  cost: number;
  time: number;
  estimated_cost: number;
  estimated_minutes: number;
  priority: string;
  required_capability: string;
  purpose: string;
  database_gap_id: string | null;
  feasible: boolean;
  infeasibility_reason: string | null;
};

export type IntelligenceGap = {
  incident_id: string;
  decision_id: string;
  evidence_id: string;
  priority: string;
  reason: string;
  target_hypothesis?: string;
  database_gap_id: string | null;
};

export type IntelligenceState = {
  evidence_id: string;
  state: string;
  reason: string;
};

export type Hypothesis = {
  id: string;
  code: string;
  title: string;
  description: string;
  status: string;
  support_score: number;
};

export type CollectionActor = {
  id: string;
  code: string;
  name: string;
  actor_type: string;
  capabilities: string[];
  location_name: string | null;
  available: boolean;
  capacity: number;
  turnaround_minutes: number | null;
};

export type IntelligenceOverview = {
  graph: Array<Record<string, unknown>>;
  states: IntelligenceState[];
  gaps: IntelligenceGap[];
  ranking: { results: RankingResult[] };
  profiles: CandidateProfile[];
  hypotheses: Hypothesis[];
  actors: CollectionActor[];
};

export type RequestStatus =
  | "DRAFT"
  | "REQUESTED"
  | "ACCEPTED"
  | "COLLECTING"
  | "SUBMITTED"
  | "VERIFIED"
  | "INGESTED"
  | "DECISION_UPDATED"
  | "REJECTED";

export type RequestStatusEvent = {
  id: string;
  request_id: string;
  from_status: string | null;
  to_status: RequestStatus;
  actor_name: string;
  note: string | null;
  occurred_at: string;
};

export type RequestAttachment = {
  id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  sha256: string;
  created_at: string;
};

export type EvidenceRequest = {
  id: string;
  incident_id: string;
  decision_id: string;
  evidence_gap_id: string | null;
  assigned_actor_id: string | null;
  result_evidence_id: string | null;
  requested_evidence_code: string;
  purpose: string;
  priority: string;
  status: RequestStatus;
  estimated_cost: number | null;
  estimated_minutes: number | null;
  requested_by: string;
  created_at: string;
  updated_at: string;
  status_events: RequestStatusEvent[];
  attachments: RequestAttachment[];
};

export type AuditEvent = {
  id: string;
  incident_id: string | null;
  entity_type: string;
  entity_id: string;
  event_type: string;
  actor_name: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type ObservationIngestResult = {
  observation_id: string;
  evidence_id: string;
  incident_id: string;
  request_id: string;
  decision_id: string;
  request_status: string;
  decision_version: number;
  uncertainty_level: string;
  value: string;
  hypothesis_updates?: Array<{
    hypothesis_id: string;
    hypothesis_code: string;
    title: string;
    previous_status: string;
    new_status: string;
    previous_support_score: number;
    new_support_score: number;
    direction: string;
    triggering_evidence_id: string;
    rationale: string;
  }>;
};
