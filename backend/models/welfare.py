from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


RiskBand = Literal["Low", "Moderate", "High"]
FusionState = Literal["REVIEW_RECOMMENDED", "MONITOR", "VERIFY_DATA"]


class PersonnelCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    service_number: str = Field(min_length=2, max_length=40)
    rank: str = Field(default="Personnel", max_length=60)
    unit: str = Field(default="Unassigned unit", max_length=120)
    posting: str = Field(default="Current posting", max_length=120)


class Personnel(PersonnelCreate):
    id: str
    created_at: datetime


class RecordResponse(BaseModel):
    id: str
    personnel_id: str
    created_at: datetime
    payload: dict[str, Any]


class InterventionCreate(BaseModel):
    personnel_id: str
    intervention_type: str = Field(min_length=2, max_length=100)
    notes: str = Field(min_length=2, max_length=2000)
    owner: str = Field(default="Welfare officer", max_length=120)
    # Task 4G: the three canonical statuses were added so legacy serialization
    # stays compatible with intervention documents written by the Task 4G
    # endpoints (single shared db.interventions collection).
    status: Literal["NEW", "UNDER REVIEW", "SUPPORT INITIATED", "FOLLOW-UP", "RESOLVED", "Open", "In progress", "Closed", "OPEN", "FOLLOW_UP", "CLOSED"] = "NEW"
    human_assessment: str = Field(default="Not yet recorded", max_length=2000)
    follow_up_date: str | None = Field(default=None, max_length=20)


class Intervention(InterventionCreate):
    id: str
    created_at: datetime


class PredictRequest(BaseModel):
    """Production inference input: raw weekly records only.

    ``features`` was removed as a request field. Client-supplied engineered
    44-feature vectors are rejected at the schema boundary (``extra="forbid"``)
    and the 44 features are always derived server-side by
    ``lib.feature_engineering``.
    """

    model_config = ConfigDict(extra="forbid")

    personnel_id: str | None = Field(default=None, max_length=120)
    raw_records: list[dict[str, Any]]


class Contribution(BaseModel):
    feature: str
    contribution: float
    direction: Literal["increases", "decreases", "neutral"]


class ClassProbability(BaseModel):
    band: RiskBand
    probability: float


class TrajectoryPoint(BaseModel):
    assessed_at: datetime
    band: RiskBand
    probability: float


class ChangedFeature(BaseModel):
    feature: str
    previous: float
    current: float
    delta: float


class EarlyWarning(BaseModel):
    status: Literal["human_review", "watch", "not_available"]
    label: str
    basis: str


class TrustComponents(BaseModel):
    completeness: float = Field(ge=0, le=100)
    recency: float = Field(ge=0, le=100)
    source_reliability: float = Field(ge=0, le=100)
    consistency: float = Field(ge=0, le=100)


class DataTrust(BaseModel):
    score: float = Field(ge=0, le=100)
    threshold: float = Field(ge=0, le=100)
    label: Literal["High", "Adequate", "Low"]
    basis: str
    components: TrustComponents


class DecisionSupport(BaseModel):
    state: FusionState
    abstained: bool
    basis: str


class PredictionResponse(BaseModel):
    assessment_id: str
    personnel_id: str | None
    predicted_band: RiskBand
    risk_probability: float
    class_probabilities: list[ClassProbability]
    prediction_confidence: float
    confidence_basis: str
    data_trust: DataTrust
    decision_support: DecisionSupport
    top_contributing_factors: list[Contribution]
    trajectory: list[TrajectoryPoint]
    trajectory_status: Literal["derived_from_history", "single_assessment"]
    early_warning: EarlyWarning
    what_changed: list[ChangedFeature] | None
    welfare_recommendations: list[str]
    derived_outputs: list[str]
    model_version: str
    feature_version: str
    assessed_at: datetime


class ModelInfo(BaseModel):
    product_name: str
    model_version: str
    feature_version: str
    feature_count: int
    feature_list_in_order: list[str]
    band_order: list[RiskBand]
    supports_probability: bool
    supports_contributions: bool
    preprocessing_status: str
    preprocessing_note: str
    limitations: list[str]


class Overview(BaseModel):
    personnel_count: int
    assessments_today: int
    open_interventions: int
    high_risk_latest: int


class DemoHistory(BaseModel):
    assessed_at: datetime
    band: RiskBand
    probability: float
    trust_score: float | None = Field(default=None, ge=0, le=100)
    fusion_state: FusionState | None = None


class DemoPersonnel(BaseModel):
    id: str
    name: str
    service_number: str
    rank: str
    unit: str
    posting: str
    is_demo_data: bool
    features: dict[str, float]
    raw_records: list[dict[str, Any]]
    summary: dict[str, Any]
    history: list[DemoHistory]


class DemoSeedResponse(BaseModel):
    seeded_count: int
    message: str


# --- Task 3C: Data-isolation + privacy response models ---


class OfficerAssessment(BaseModel):
    """WELFARE_OFFICER — Minimized assessment record.

    Strips internal/technical fields (features, date_key, is_latest,
    confidence_basis) that are not needed by the officer dashboard.
    """

    id: str
    personnel_id: str
    assessed_at: datetime
    predicted_band: RiskBand
    risk_probability: float
    prediction_confidence: float
    class_probabilities: list[ClassProbability]
    top_contributing_factors: list[Contribution]
    data_trust: DataTrust
    decision_support: DecisionSupport
    model_version: str
    feature_version: str


class PersonnelPredictionResponse(BaseModel):
    """PERSONNEL — Safe prediction envelope.

    Returned after a PERSONNEL /predict call.  Contains only submission
    confirmation metadata; no risk band, probability, SHAP, what-changed,
    recommendations, trajectory, trust or decision-support fields.
    """

    assessment_id: str
    personnel_id: str
    assessed_at: datetime
    status: Literal["recorded"]
    message: str


class PersonnelRecord(BaseModel):
    """PERSONNEL — Safe self-service record envelope.

    Read-only view of a record the authenticated personnel submitted.
    Scoped server-side; no client-supplied personnel_id accepted.
    """

    id: str
    collection: str
    created_at: datetime
    payload: dict[str, Any]


class PersonnelAssessment(BaseModel):
    """PERSONNEL — Safe self-service assessment timestamp.

    Contains only the assessment identity and when it was recorded.
    No risk intelligence, probability, SHAP, trust or decision data.
    """

    assessment_id: str
    assessed_at: datetime


# --- Task 4A: Welfare intelligence historical retrieval ---


class HistoryRecord(BaseModel):
    """One stored document in a personnel's welfare history.

    ``event_at`` is the effective chronological timestamp the retrieval layer
    sorted on (``created_at`` for welfare/workload/deployment/leave records,
    ``assessed_at`` for risk assessments).  It is None only when the source
    document carries no usable timestamp, in which case the record sorts after
    all timestamped records (deterministically by ``id``).
    """

    id: str
    collection: str
    event_at: datetime | None = None
    payload: dict[str, Any]


class HistorySection(BaseModel):
    """A single collection's history for one personnel.

    ``present`` marks whether ANY document was found for the personnel in this
    collection.  ``present=false`` means missing data (never fabricated);
    ``present=true`` does not imply non-zero values — zero-valued records are
    still returned as real historical data.
    """

    present: bool
    record_count: int
    records: list[HistoryRecord]


class PersonnelHistory(BaseModel):
    """WELFARE_OFFICER — Longitudinal welfare/workload history for one
    authorized personnel record.

    Collects static personnel info, wellness logs, workload records,
    deployment history, leave requests and existing risk assessments into a
    deterministic chronological envelope.  Stored assessments are minimized
    exactly like OfficerAssessment: the 44-feature vector, date_key, is_latest
    and confidence_basis are never exposed.
    """

    personnel_id: str
    personnel: dict[str, Any] | None = None
    sections: dict[str, HistorySection]
    generated_at: datetime
    notes: list[str]


# --- Task 4B: Exact 4-week raw-record intelligence window ---


class RawWindowRecord(BaseModel):
    """One raw weekly record in the 4-week window.

    The static/raw values are deliberately untyped (``Any``) so stored values
    are forwarded exactly as they exist — no coercion, no imputation.  Missing
    values are None.  The fixed column set mirrors
    ``lib.feature_engineering.REQUIRED_RAW_COLUMNS`` so the output can be
    passed straight into the existing feature-engineering pipeline.
    """

    personnel_id: str
    week: int
    years_of_service: Any = None
    hardship_posting_flag: Any = None
    transfer_count_24mo: Any = None
    years_in_current_posting: Any = None
    weekly_duty_hours: Any = None
    night_shift_ratio: Any = None
    overtime_hours: Any = None
    days_since_last_rest: Any = None
    days_since_last_leave: Any = None
    leave_balance: Any = None
    wellness_score_self_report: Any = None
    sleep_quality_score_self_report: Any = None
    resting_hr_trend_biometric: Any = None
    sleep_hours_biometric: Any = None


class PersonnelRawWindow(BaseModel):
    """WELFARE_OFFICER — Exact 4-week raw-record window for one personnel.

    ``raw_records`` are ordered chronologically (week 0 oldest .. week 3
    latest) and are ready to be passed directly to the existing feature
    engineering and inference layers.  Missing weeks are represented by records
    whose raw fields are None — nothing is fabricated.
    """

    personnel_id: str
    personnel: dict[str, Any] | None = None
    raw_records: list[RawWindowRecord]
    window_start: datetime
    window_end: datetime
    latest_observation_date: datetime
    week_count: int
    weeks_with_data: list[int]
    notes: list[str]


# --- Task 4C: Dedicated welfare prediction (Welfare Officer) ---


class DataSufficiency(BaseModel):
    """Window-level data adequacy summary attached to a welfare prediction.

    Tells the officer exactly how much raw welfare history supported the run.
    Missing weeks are never fabricated: ``weeks_with_data`` lists only the
    weeks that actually carried timestamped observations.
    """

    week_count: int
    weeks_with_data: list[int]
    latest_observation_date: datetime
    basis: str


class WelfarePredictionResponse(BaseModel):
    """WELFARE_OFFICER — Model-backed welfare prediction for ONE personnel.

    Produced from the stored 4-week raw window through the canonical
    feature-engineering pipeline and the calibrated model by
    ``lib.welfare_prediction``.  Deliberately excludes the 44-feature vector,
    model filenames, artifact paths and credentials; insufficient stored data
    yields ``PredictionUnavailable`` instead of a fabricated prediction.
    """

    personnel_id: str
    predicted_band: RiskBand
    risk_probability: float
    class_probabilities: list[ClassProbability]
    prediction_confidence: float
    confidence_basis: str
    top_contributing_factors: list[Contribution]
    data_trust: DataTrust
    decision_support: DecisionSupport
    welfare_recommendations: list[str]
    data_sufficiency: DataSufficiency
    model_version: str
    feature_version: str
    assessed_at: datetime
    derived_outputs: list[str]


class PredictionUnavailable(BaseModel):
    """Safe structured envelope when a model-backed prediction is not possible.

    Returned instead of guessing or fabricating a risk signal (no band,
    probability, contributions, trust or feature data).  ``reason`` is a safe
    machine-readable label; ``message`` is an officer-readable explanation.
    """

    status: Literal["insufficient_data"]
    personnel_id: str
    reason: str
    message: str


# --- Task 4D: Welfare risk trajectory and early warning (Welfare Officer) ---


class PredictionSnapshot(BaseModel):
    """One minimized trajectory point.

    Carries only the model's band and probability for a prediction; the
    44-feature vector, class probabilities and internal confidence material are
    deliberately excluded from the officer trajectory envelope.
    """

    assessed_at: datetime
    predicted_band: RiskBand
    risk_probability: float


class WelfareTrajectoryResponse(BaseModel):
    """WELFARE_OFFICER — Risk trajectory and early warning for ONE personnel.

    Combines the Task 4C live prediction with the stored assessment history
    into a chronological risk trajectory.  ``trend`` is ``increasing`` /
    ``decreasing`` / ``stable`` / ``insufficient_data`` (a direction requires at
    least two chronologically ordered points; missing temporal evidence never
    fabricates one).  ``early_warning`` is a TEMPORAL signal — it can never fire
    from a single assessment or missing history.
    """

    personnel_id: str
    trend: Literal["increasing", "decreasing", "stable", "insufficient_data"]
    early_warning: EarlyWarning
    history: list[PredictionSnapshot]
    prediction: PredictionSnapshot
    evidence_basis: str
    assessed_at: datetime
    derived_outputs: list[str]


# --- Task 4E: Explainable welfare AI (Welfare Officer) ---


class ExplanationFactor(BaseModel):
    """One top contributing factor with an officer-readable display label.

    ``feature`` carries the PUBLIC metadata factor name (the same surface the
    4C/4D endpoints already expose for contributions); the raw engineered
    44-feature vector, model filenames, artifact paths and credentials are never
    returned.
    """

    feature: str
    display_name: str
    contribution: float
    direction: Literal["increases", "decreases", "neutral"]
    impact_summary: str


class WhatChangedItem(BaseModel):
    """One observable current-vs-prior change.

    Only factors observed in BOTH periods are reported; missing data is never
    shown as improvement or deterioration.  ``impact`` describes movement of the
    model's risk signal (decision support) and is ``unknown`` whenever a
    per-factor direction is not reliably available.
    """

    feature: str
    display_name: str
    previous: float
    current: float
    delta: float
    change: Literal["increased", "decreased"]
    contribution_direction: Literal["increases", "decreases", "neutral", "unknown"]
    impact: Literal["increases_risk_signal", "decreases_risk_signal", "unknown"]


class WhatChangedSummary(BaseModel):
    """Temporal 'What Changed?' envelope.

    ``status`` is ``available`` when a comparison was possible (even with no
    material change inside the materiality threshold) and ``insufficient_data``
    when no usable prior temporal evidence exists — nothing is invented.
    """

    status: Literal["available", "insufficient_data"]
    comparison: Literal["prior_assessment", "prior_week"] | None = None
    basis: str
    no_material_change: bool = False
    changes: list[WhatChangedItem] = Field(default_factory=list)


class ExplanationPredictionSummary(BaseModel):
    """Compact prediction reference for the explanation envelope.

    Mirrors the officer-facing risk signal; no class probabilities or internal
    confidence material beyond what the dedicated 4C/4D endpoints already expose.
    """

    predicted_band: RiskBand
    risk_probability: float


class WelfareExplanationResponse(BaseModel):
    """WELFARE_OFFICER — Explainable welfare signal for ONE personnel.

    Decision-support explanation built from the existing Task 4C prediction and
    the existing temporal evidence.  ``explanation_status`` is ``available``, or
    ``explanation_unavailable`` when native per-factor contributions cannot be
    produced for the artifact (the risk signal itself is unchanged).  Never
    exposes the 44-feature vector, model filenames, artifact paths, credentials,
    or unnecessary raw personnel records.
    """

    personnel_id: str
    explanation_status: Literal["available", "explanation_unavailable"]
    status_message: str
    prediction: ExplanationPredictionSummary
    explanation_method: Literal["native_feature_contributions"]
    top_contributing_factors: list[ExplanationFactor]
    what_changed: WhatChangedSummary
    evidence_basis: str
    derived_outputs: list[str]
    assessed_at: datetime


class ExplanationUnavailable(BaseModel):
    """Safe structured envelope when an explanation cannot be produced.

    Returned instead of guessing or fabricating an explanation (no prediction,
    contribution, change or feature data).  ``reason`` is a safe machine-readable
    label; ``message`` is an officer-readable explanation.
    """

    status: Literal["insufficient_data"]
    personnel_id: str
    reason: str
    message: str


# --- Task 4F: Risk + Trust Fusion & Safe Abstention ---

DecisionSupportState = Literal[
    "SUPPORTED",
    "LIMITED_EVIDENCE",
    "INSUFFICIENT_EVIDENCE",
]


class EvidenceQuality(BaseModel):
    """WELFARE_OFFICER — Deterministic evidence-quality assessment for one
    personnel record.

    Derived from information already available in the production pipeline:
    window completeness, temporal coverage, observation validity, data
    recency, source reliability and consistency.  This is explicitly
    NOT model confidence; it measures how much reliable evidence is
    available for the model to reason over.

    Every component weight and threshold is explicitly documented and
    deterministic.  Absence of data is never treated as evidence of
    improvement or deterioration.
    """

    score: float = Field(ge=0, le=100)
    threshold: float = Field(ge=0, le=100)
    label: Literal["Sufficient", "Limited", "Insufficient"]
    basis: str
    components: TrustComponents
    temporal_coverage_weeks: int = Field(ge=0, le=4)
    invalid_observations_detected: bool


class WelfareDecisionSupportResponse(BaseModel):
    """WELFARE_OFFICER — Comprehensive risk + trust fusion for ONE personnel.

    Task 4F: synthesizes the existing Phase 4C prediction, 4D trajectory, and
    4E explanation into a single decision-support envelope with explicit evidence
    quality assessment and safe abstention.

    The model output is NEVER silently modified by the trust layer.  When
    evidence is insufficient, the system abstains (``decision_state`` =
    ``INSUFFICIENT_EVIDENCE``) and provides sanitized evidence-quality
    information rather than a misleading risk conclusion.

    Access: WELFARE_OFFICER only.  The 44-feature vector, model filenames,
    artifact paths, credentials and unnecessary raw personnel records are
    never returned.
    """

    personnel_id: str
    decision_state: DecisionSupportState
    decision_basis: str

    prediction_available: bool
    predicted_band: RiskBand | None = None
    risk_probability: float | None = None
    class_probabilities: list[ClassProbability] | None = None
    prediction_confidence: float | None = None
    confidence_basis: str | None = None
    top_contributing_factors: list[Contribution] | None = None

    evidence_quality: EvidenceQuality
    data_sufficiency: DataSufficiency

    trajectory_available: bool
    trend: Literal["increasing", "decreasing", "stable", "insufficient_data"] | None = None
    early_warning: EarlyWarning | None = None

    temporal_analysis_available: bool
    what_changed: WhatChangedSummary | None = None

    welfare_recommendations: list[str]
    derived_outputs: list[str]
    assessed_at: datetime


# --- Task 4G: Welfare Intervention & Action Tracking ---

InterventionType = Literal[
    "CHECK_IN",
    "COUNSELLING_REFERRAL",
    "REST_RECOMMENDATION",
    "LEAVE_SUPPORT",
    "MEDICAL_REFERRAL",
    "OTHER",
]

InterventionStatus = Literal[
    "OPEN",
    "FOLLOW_UP",
    "CLOSED",
]


class InterventionActionCreate(BaseModel):
    """WELFARE_OFFICER — Create an intervention / welfare action for ONE
    personnel.

    ``personnel_id`` is deliberately NOT a body field: it is taken from the
    URL path only, so a client can never re-direct an intervention to a
    different personnel by tampering with the request body.  ``extra="forbid"``
    rejects any unknown field (including attempted ``welfare_officer_id`` /
    role / user-id smuggling) at the schema boundary.  The acting officer is
    derived server-side from the authenticated token.
    """

    model_config = ConfigDict(extra="forbid")

    intervention_type: InterventionType
    reason: str = Field(min_length=2, max_length=300)
    notes: str = Field(min_length=2, max_length=2000)
    status: InterventionStatus = "OPEN"
    follow_up_at: datetime | None = None
    outcome: str | None = Field(default=None, max_length=500)
    outcome_notes: str | None = Field(default=None, max_length=2000)


class InterventionActionUpdate(BaseModel):
    """WELFARE_OFFICER — Update the mutable lifecycle fields of an intervention.

    At least one field must be supplied (an empty body is rejected).  Identity
    fields (intervention_id, personnel_id, welfare_officer_id) can never be
    supplied by the client.
    """

    model_config = ConfigDict(extra="forbid")

    status: InterventionStatus | None = None
    outcome: str | None = Field(default=None, max_length=500)
    outcome_notes: str | None = Field(default=None, max_length=2000)
    follow_up_at: datetime | None = None


class InterventionAction(BaseModel):
    """WELFARE_OFFICER — One stored welfare intervention on a personnel record.

    ``welfare_officer_id`` is captured server-side from the authenticated token
    at creation time.  Intervention documents written by the legacy Phase 3
    endpoints are normalized on read: free-text legacy ``status`` maps onto the
    closest Task 4G status and unknown action types map to ``OTHER``.
    """

    intervention_id: str
    personnel_id: str
    welfare_officer_id: str | None = None
    created_at: datetime
    intervention_type: InterventionType
    reason: str | None = None
    notes: str
    status: InterventionStatus
    follow_up_at: datetime | None = None
    outcome: str | None = None
    outcome_notes: str | None = None
    updated_at: datetime | None = None
