export type RiskBand = "Low" | "Moderate" | "High";

export type UserRole = "PERSONNEL" | "WELFARE_OFFICER" | "COMMANDER" | "ADMIN";

export interface AuthToken {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
  role: UserRole;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface ModelInfo {
  product_name: string;
  model_version: string;
  feature_version: string;
  feature_count: number;
  feature_list_in_order: string[];
  band_order: RiskBand[];
  supports_probability: boolean;
  supports_contributions: boolean;
  preprocessing_status: string;
  preprocessing_note: string;
  limitations: string[];
}

export interface Overview {
  personnel_count: number;
  assessments_today: number;
  open_interventions: number;
  high_risk_latest: number;
}

export interface UnitOverview {
  unit: string;
  personnel_count: number | null;
  high_risk_latest: number | null;
  suppressed: boolean;
}

export interface UnitOverviewResponse {
  units: UnitOverview[];
  total_personnel_count: number;
  high_risk_latest_total: number;
  min_group_size: number;
  suppressed_units: number;
  generated_at: string;
}

export interface Contribution {
  feature: string;
  contribution: number;
  direction: "increases" | "decreases" | "neutral";
}

export interface ClassProbability {
  band: RiskBand;
  probability: number;
}

export interface TrajectoryPoint {
  assessed_at: string;
  band: RiskBand;
  probability: number;
}

export interface ChangedFeature {
  feature: string;
  previous: number;
  current: number;
  delta: number;
}

export interface EarlyWarning {
  status: "human_review" | "watch" | "not_available";
  label: string;
  basis: string;
}

export interface DataTrust {
  score: number;
  threshold: number;
  label: "High" | "Adequate" | "Low";
  basis: string;
  components: {
    completeness: number;
    recency: number;
    source_reliability: number;
    consistency: number;
  };
}

export interface DecisionSupport {
  state: "REVIEW_RECOMMENDED" | "MONITOR" | "VERIFY_DATA";
  abstained: boolean;
  basis: string;
}

export interface PredictionResponse {
  assessment_id: string;
  personnel_id: string | null;
  predicted_band: RiskBand;
  risk_probability: number;
  class_probabilities: ClassProbability[];
  prediction_confidence: number;
  confidence_basis: string;
  data_trust: DataTrust;
  decision_support: DecisionSupport;
  top_contributing_factors: Contribution[];
  trajectory: TrajectoryPoint[];
  trajectory_status: "derived_from_history" | "single_assessment";
  early_warning: EarlyWarning;
  what_changed: ChangedFeature[] | null;
  welfare_recommendations: string[];
  derived_outputs: string[];
  model_version: string;
  feature_version: string;
  assessed_at: string;
}

export interface Personnel {
  id: string;
  name: string;
  service_number: string;
  rank: string;
  unit: string;
  posting: string;
  created_at: string;
}

export interface PersonnelCreate {
  name: string;
  service_number: string;
  rank?: string;
  unit?: string;
  posting?: string;
}

export interface PredictRequest {
  personnel_id?: string | null;
  raw_records: RawWelfareRecord[];
}

export interface RawWelfareRecord {
  personnel_id: string;
  week: number;
  years_of_service: number;
  hardship_posting_flag: number | boolean;
  transfer_count_24mo: number;
  years_in_current_posting: number;
  weekly_duty_hours: number | null;
  night_shift_ratio: number | null;
  overtime_hours: number | null;
  days_since_last_rest: number | null;
  days_since_last_leave: number | null;
  leave_balance: number | null;
  wellness_score_self_report: number | null;
  sleep_quality_score_self_report: number | null;
  resting_hr_trend_biometric: number | null;
  sleep_hours_biometric: number | null;
}

export interface RecordResponse {
  id: string;
  personnel_id: string;
  created_at: string;
  payload: Record<string, unknown>;
}

export interface InterventionCreate {
  personnel_id: string;
  intervention_type: string;
  notes: string;
  owner?: string;
  status?: InterventionStatus;
  human_assessment?: string;
  follow_up_date?: string | null;
}

export type InterventionStatus = "NEW" | "UNDER REVIEW" | "SUPPORT INITIATED" | "FOLLOW-UP" | "RESOLVED" | "Open" | "In progress" | "Closed";

export interface Intervention extends InterventionCreate {
  id: string;
  created_at: string;
  owner: string;
  status: InterventionStatus;
  human_assessment: string;
  follow_up_date: string | null;
}

export interface DemoHistory {
  assessed_at: string;
  band: RiskBand;
  probability: number;
  trust_score?: number;
  fusion_state?: "REVIEW_RECOMMENDED" | "MONITOR" | "VERIFY_DATA";
}

export interface DemoPersonnel {
  id: string;
  name: string;
  service_number: string;
  rank: string;
  unit: string;
  posting: string;
  is_demo_data: boolean;
  features: Record<string, number>;
  raw_records: RawWelfareRecord[];
  summary: Record<string, string>;
  history: DemoHistory[];
}

export interface DemoSeedResponse {
  seeded_count: number;
  message: string;
}

// --- Welfare brief APIs (Task 4E explanation + Task 4G interventions) ---

export interface ExplanationFactor {
  feature: string;
  display_name: string;
  contribution: number;
  direction: "increases" | "decreases" | "neutral";
  impact_summary: string;
}

export interface BriefWhatChange {
  feature: string;
  display_name: string;
  previous: number;
  current: number;
  delta: number;
  change: "increased" | "decreased";
  contribution_direction: "increases" | "decreases" | "neutral" | "unknown";
  impact: "increases_risk_signal" | "decreases_risk_signal" | "unknown";
}

export interface BriefWhatChangedSummary {
  status: "available" | "insufficient_data";
  comparison?: "prior_assessment" | "prior_week" | null;
  basis: string;
  no_material_change?: boolean;
  changes: BriefWhatChange[];
}

export interface WelfareExplanationResponse {
  personnel_id: string;
  explanation_status: "available" | "explanation_unavailable";
  status_message: string;
  prediction: { predicted_band: RiskBand; risk_probability: number };
  explanation_method: "native_feature_contributions";
  top_contributing_factors: ExplanationFactor[];
  what_changed: BriefWhatChangedSummary;
  evidence_basis: string;
  derived_outputs: string[];
  assessed_at: string;
}

export interface ExplanationUnavailable {
  status: "insufficient_data";
  personnel_id: string;
  reason: string;
  message: string;
}

export type InterventionActionStatus = "OPEN" | "FOLLOW_UP" | "CLOSED";
export type InterventionActionType =
  | "CHECK_IN"
  | "COUNSELLING_REFERRAL"
  | "REST_RECOMMENDATION"
  | "LEAVE_SUPPORT"
  | "MEDICAL_REFERRAL"
  | "OTHER";

export interface InterventionAction {
  intervention_id: string;
  personnel_id: string;
  welfare_officer_id?: string | null;
  created_at: string;
  intervention_type: InterventionActionType;
  reason?: string | null;
  notes: string;
  status: InterventionActionStatus;
  follow_up_at?: string | null;
  outcome?: string | null;
  outcome_notes?: string | null;
  updated_at?: string | null;
}

// --- Admin realm (Task 5.5): account provisioning + system status ---

// Provisioning never accepts ADMIN: the backend Literal forbids it at the schema.
export type ProvisionRole = "WELFARE_OFFICER" | "COMMANDER";

export interface AdminProvisionRequest {
  username: string;
  password: string;
  role: ProvisionRole;
}

export interface AdminUserSummary {
  id: string;
  username: string;
  role: UserRole;
  active: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface AdminAuthStatus {
  provider: string;
  algorithm: string;
  token_expire_minutes: number;
  session_boundary_clear_on_signout: boolean;
  active_accounts: number;
}

export interface AdminDatabaseStatus {
  status: "ok" | "unreachable";
}

export interface AdminModelStatus {
  product_name?: string | null;
  model_version?: string | null;
  feature_version?: string | null;
  feature_count?: number | null;
  preprocessing_status?: string | null;
  ready: boolean;
}

export interface AdminSystemStatus {
  authentication: AdminAuthStatus;
  database: AdminDatabaseStatus;
  model: AdminModelStatus | null;
}