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
    status: Literal["NEW", "UNDER REVIEW", "SUPPORT INITIATED", "FOLLOW-UP", "RESOLVED", "Open", "In progress", "Closed"] = "NEW"
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
