from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


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
    personnel_id: str | None = Field(default=None, max_length=120)
    features: dict[str, float]


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
    summary: dict[str, Any]
    history: list[DemoHistory]


class DemoSeedResponse(BaseModel):
    seeded_count: int
    message: str
