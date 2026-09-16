from datetime import datetime, timedelta, timezone
from typing import Any, Union
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request, status

from lib.audit_service import log_denial
from lib.db import db
from lib.feature_engineering import (
    RAW_NUMERIC_FEATURES,
    STATIC_FEATURES,
    records_to_frame,
)
from lib.inference import InferenceEngine, ModelArtifactError, utc_now
from lib.rbac_deps import require_any_role, require_personnel, require_welfare_officer
from models.welfare import (
    DataTrust,
    DecisionSupport,
    EarlyWarning,
    Intervention,
    InterventionCreate,
    DemoPersonnel,
    DemoSeedResponse,
    ModelInfo,
    OfficerAssessment,
    Overview,
    Personnel,
    PersonnelAssessment,
    PersonnelCreate,
    PersonnelPredictionResponse,
    PersonnelRecord,
    PredictRequest,
    PredictionResponse,
    RecordResponse,
    TrajectoryPoint,
)


router = APIRouter()
TRUST_ABSTENTION_THRESHOLD = 60.0
PERSONNEL_RECORD_COLLECTIONS = {"wellness_logs", "workload_records", "deployment_history", "leave_requests"}
engine = InferenceEngine()
try:
    engine.load()
except ModelArtifactError:
    # Keep the shell and model-info endpoint available if an environment is
    # served without artifacts; /predict reports the actionable load error.
    pass


def _ensure_engine_ready() -> None:
    """Return an actionable service error for any model-backed demo flow."""
    if engine.load_error or engine.risk_model is None or engine.preprocessing_pipeline is None:
        raise HTTPException(
            status_code=503,
            detail=f"AI model artifacts are unavailable: {engine.load_error or 'risk model or preprocessing pipeline is not loaded'}",
        )


def _validate_raw_records(raw_records: list[dict[str, Any]]) -> pd.DataFrame:
    """Strictly control the inference entry point: build and validate a raw
    weekly record frame, rejecting pre-engineered or unknown columns. The 44
    features are always derived server-side by the canonical pipeline."""
    try:
        return records_to_frame(raw_records)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _recommendations(band: str) -> list[str]:
    if band == "High":
        return [
            "Route for prompt human welfare officer review.",
            "Offer a voluntary welfare check-in and review rest, workload and leave context.",
            "Do not use this signal for diagnosis, discipline or automated messaging.",
        ]
    if band == "Moderate":
        return [
            "Offer a voluntary welfare check-in with a trained human officer.",
            "Review recent duty hours, rest access and leave availability with context.",
            "Keep the assessment private and treat it as decision support only.",
        ]
    return [
        "Continue routine welfare touchpoints and voluntary self-reporting.",
        "Keep rest, leave and workload data current for future longitudinal review.",
        "Treat the model as one signal, never as a diagnosis or disciplinary input.",
    ]


async def _history(personnel_id: str | None, current_id: str | None = None) -> list[dict[str, Any]]:
    if not personnel_id:
        return []
    query: dict[str, Any] = {"personnel_id": personnel_id}
    docs = await db.risk_assessments.find(query).sort("assessed_at", 1).to_list(20)
    return [doc for doc in docs if doc.get("id") != current_id]


def _trajectory_direction(points: list[dict[str, Any]]) -> str:
    """Classify the two newest points after sorting chronologically."""
    def chronology_key(point: dict[str, Any]) -> float:
        value = point["assessed_at"]
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            return value.timestamp()
        return 0.0

    valid = sorted(
        (point for point in points if point.get("assessed_at") is not None),
        key=chronology_key,
    )
    if len(valid) < 2:
        return "insufficient_history"
    previous = float(valid[-2].get("risk_probability", valid[-2].get("probability", 0.0)))
    current = float(valid[-1].get("risk_probability", valid[-1].get("probability", 0.0)))
    if current > previous + 1e-9:
        return "rising"
    if current < previous - 1e-9:
        return "falling"
    return "stable"


def _early_warning(band: str, trajectory: list[dict[str, Any]]) -> EarlyWarning:
    if band == "High":
        return EarlyWarning(status="human_review", label="Human review recommended", basis="Current model band is High")
    direction = _trajectory_direction(trajectory)
    if direction == "rising":
        return EarlyWarning(status="watch", label="Watch rising trajectory", basis="The two newest chronologically ordered assessments show rising risk probability")
    if direction == "falling":
        return EarlyWarning(status="not_available", label="Risk probability easing", basis="The two newest chronologically ordered assessments show falling risk probability")
    if direction == "stable":
        return EarlyWarning(status="not_available", label="Risk probability stable", basis="The two newest chronologically ordered assessments show no material probability change")
    return EarlyWarning(status="not_available", label="No trajectory signal", basis="A direction requires at least two chronologically ordered assessments")


def _data_trust(features: dict[str, float]) -> DataTrust:
    """Deterministic data-quality heuristic, explicitly separate from model confidence.

    Completeness uses the model's original-source missingness flags; recency is
    full because /predict is a live assessment; source reliability is a fixed
    documented blend for authorized organizational, voluntary self-report and
    optional biometric inputs; consistency checks current values against their
    rolling means without changing the risk prediction.
    """
    missing_flags = [float(value) for name, value in features.items() if name.endswith("__was_missing")]
    completeness = 100.0 if not missing_flags else 100.0 * (1.0 - sum(min(max(value, 0.0), 1.0) for value in missing_flags) / len(missing_flags))
    recency = 100.0
    source_reliability = 85.0
    consistency_checks: list[float] = []
    for name, value in features.items():
        if "__" in name or f"{name}__roll4_mean" not in features:
            continue
        rolling = float(features[f"{name}__roll4_mean"])
        scale = max(abs(float(value)), abs(rolling), 1.0)
        consistency_checks.append(max(0.0, 100.0 - min(100.0, abs(float(value) - rolling) / scale * 100.0)))
    consistency = sum(consistency_checks) / len(consistency_checks) if consistency_checks else 75.0
    score = round(0.45 * completeness + 0.20 * recency + 0.20 * source_reliability + 0.15 * consistency, 1)
    label = "High" if score >= 80 else "Adequate" if score >= TRUST_ABSTENTION_THRESHOLD else "Low"
    return DataTrust(
        score=score,
        threshold=TRUST_ABSTENTION_THRESHOLD,
        label=label,
        basis="Heuristic data-quality score from original-source completeness, live-request recency, documented source reliability and current-vs-rolling consistency; it is not model confidence.",
        components={
            "completeness": round(completeness, 1),
            "recency": recency,
            "source_reliability": source_reliability,
            "consistency": round(consistency, 1),
        },
    )


def _decision_support(band: str, trust: DataTrust, direction: str) -> DecisionSupport:
    if trust.score < trust.threshold:
        return DecisionSupport(
            state="VERIFY_DATA",
            abstained=True,
            basis=f"Data trust {trust.score:.1f} is below the {trust.threshold:.0f} actionability threshold; verify evidence before acting on model risk.",
        )
    if band == "High" or direction == "rising":
        return DecisionSupport(
            state="REVIEW_RECOMMENDED",
            abstained=False,
            basis="Sufficient data trust with a High current band or rising chronological trajectory supports human welfare review.",
        )
    return DecisionSupport(
        state="MONITOR",
        abstained=False,
        basis="Data trust is sufficient and the current model/trajectory signal does not require prompt review.",
    )


@router.get("/model-info", response_model=ModelInfo)
async def model_info() -> ModelInfo:
    """PUBLIC — Model metadata and status."""
    _ensure_engine_ready()
    return ModelInfo(**engine.info())


@router.get("/overview", response_model=Overview)
async def overview(current_user: dict = Depends(require_any_role("WELFARE_OFFICER", "COMMANDER"))) -> Overview:
    """AGGREGATE ONLY — Operational overview (counts, no individual data).

    WELFARE_OFFICER and COMMANDER. COMMANDER is restricted to this aggregate
    view; every individual personnel/risk/wellness endpoint stays blocked
    (a Commander dashboard is a Phase 2 deliverable).
    """
    today = datetime.now(timezone.utc).date().isoformat()
    personnel_count = await db.personnel.count_documents({})
    assessments_today = await db.risk_assessments.count_documents({"date_key": today})
    open_interventions = await db.interventions.count_documents({"status": {"$in": ["NEW", "UNDER REVIEW", "SUPPORT INITIATED", "FOLLOW-UP", "Open", "In progress"]}})
    high_risk_latest = await db.risk_assessments.count_documents({"predicted_band": "High", "is_latest": True})
    return Overview(
        personnel_count=personnel_count,
        assessments_today=assessments_today,
        open_interventions=open_interventions,
        high_risk_latest=high_risk_latest,
    )


@router.get("/personnel", response_model=list[Personnel])
async def list_personnel(current_user: dict = Depends(require_welfare_officer)) -> list[Personnel]:
    """WELFARE_OFFICER — List all personnel records.

    COMMANDER is blocked from individual personnel data (Phase 2 Commander
    aggregate dashboard only).
    """
    docs = await db.personnel.find().sort("created_at", -1).to_list(100)
    return [Personnel(**doc) for doc in docs]


@router.post("/personnel", response_model=Personnel)
async def create_personnel(payload: PersonnelCreate, current_user: dict = Depends(require_welfare_officer)) -> Personnel:
    """WELFARE_OFFICER — Create personnel record."""
    doc = payload.model_dump()
    doc.update({"id": str(uuid4()), "created_at": utc_now()})
    await db.personnel.insert_one(doc)
    return Personnel(**doc)


@router.get("/assessments", response_model=list[OfficerAssessment])
async def list_assessments(current_user: dict = Depends(require_welfare_officer)) -> list[OfficerAssessment]:
    """WELFARE_OFFICER — List individual risk assessments (minimized).

    COMMANDER is blocked from individual risk data.  Internal/technical
    fields (features vector, date_key, is_latest, confidence_basis) are
    stripped so the response never exposes the 44-feature vector or the
    model artifact filename.
    """
    docs = await db.risk_assessments.find().sort("assessed_at", -1).to_list(100)
    assessments: list[OfficerAssessment] = []
    for doc in docs:
        assessments.append(
            OfficerAssessment(
                id=doc["id"],
                personnel_id=doc["personnel_id"],
                assessed_at=doc["assessed_at"],
                predicted_band=doc["predicted_band"],
                risk_probability=float(doc["risk_probability"]),
                prediction_confidence=float(doc["prediction_confidence"]),
                class_probabilities=[
                    {"band": cp["band"], "probability": float(cp["probability"])}
                    for cp in doc.get("class_probabilities", [])
                ],
                top_contributing_factors=[
                    {
                        "feature": c["feature"],
                        "contribution": float(c["contribution"]),
                        "direction": c["direction"],
                    }
                    for c in doc.get("top_contributing_factors", [])
                ],
                data_trust=DataTrust(**doc["data_trust"]),
                decision_support=DecisionSupport(**doc["decision_support"]),
                model_version=doc.get("model_version", ""),
                feature_version=doc.get("feature_version", ""),
            )
        )
    return assessments


@router.post("/predict", response_model=Union[PredictionResponse, PersonnelPredictionResponse])
async def predict(payload: PredictRequest, request: Request, current_user: dict = Depends(require_any_role("PERSONNEL", "WELFARE_OFFICER"))) -> Union[PredictionResponse, PersonnelPredictionResponse]:
    """PERSONNEL (own records only) / WELFARE_OFFICER (any personnel) — Run risk prediction.

    Response is role-aware (Task 3C data isolation):
    - WELFARE_OFFICER receives the full PredictionResponse (risk band, SHAP,
      what-changed, recommendations) with the model filename sanitized.
    - PERSONNEL receives only PersonnelPredictionResponse — submission
      confirmation metadata with NO risk intelligence.
    The same inference always runs and the full assessment is stored server-side.

    COMMANDER is blocked: individual risk data is inaccessible to the Command
    role in this phase.
    """
    # Enforce personnel ownership: PERSONNEL can only predict for themselves.
    # The authenticated user identity binds the personnel_id scope; a PERSONNEL
    # record may never reference another user's identifier (IDOR guard).  The
    # attempt is audited as an idor_denial before the 403 is raised.
    target_personnel_id = payload.personnel_id
    if current_user["role"] == "PERSONNEL":
        if target_personnel_id != current_user["user_id"]:
            await log_denial(
                "idor_denial",
                request,
                current_user,
                reason="personnel_scope_violation",
                details={"target_personnel_id": target_personnel_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Personnel can only request risk prediction for themselves",
            )
    _ensure_engine_ready()

    # Production boundary: only raw weekly records are accepted. Client-supplied
    # engineered 44-feature vectors are already rejected by PredictRequest
    # (extra="forbid"); the 44 features are derived server-side here.
    records = _validate_raw_records(payload.raw_records)
    try:
        result, features = engine.predict_from_raw_records(records, personnel_id=payload.personnel_id)
    except ModelArtifactError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    personnel_id = payload.personnel_id
    assessed_at = utc_now()
    assessment_id = str(uuid4())
    prior = await _history(personnel_id)
    previous = prior[-1] if prior else None
    trajectory = [
        TrajectoryPoint(
            assessed_at=item["assessed_at"],
            band=item["predicted_band"],
            probability=float(item["risk_probability"]),
        )
        for item in prior[-7:]
        if item.get("assessed_at") and item.get("predicted_band")
    ]
    trajectory.append(TrajectoryPoint(assessed_at=assessed_at, band=result["predicted_band"], probability=result["risk_probability"]))
    changed = None
    if previous:
        previous_features = previous.get("features", {})
        ranked = sorted(
            (
                (name, float(previous_features[name]), float(value), float(value) - float(previous_features[name]))
                for name, value in features.items()
                if name in previous_features
            ),
            key=lambda row: abs(row[3]),
            reverse=True,
        )[:5]
        changed = [{"feature": name, "previous": old, "current": current, "delta": delta} for name, old, current, delta in ranked]
    trajectory_records = [
        {"assessed_at": point.assessed_at, "risk_probability": point.probability}
        for point in trajectory
    ]
    direction = _trajectory_direction(trajectory_records)
    early_warning = _early_warning(result["predicted_band"], trajectory_records)
    trust = _data_trust(features)
    decision = _decision_support(result["predicted_band"], trust, direction)
    record = {
        "id": assessment_id,
        "personnel_id": personnel_id,
        "assessed_at": assessed_at,
        "date_key": assessed_at.date().isoformat(),
        "features": features,
        "is_latest": True,
        "data_trust": trust.model_dump(),
        "decision_support": decision.model_dump(),
        **result,
    }
    if personnel_id:
        await db.risk_assessments.update_many({"personnel_id": personnel_id, "is_latest": True}, {"$set": {"is_latest": False}})
    await db.risk_assessments.insert_one(record)

    # Task 3C: role-aware response boundary.
    # PERSONNEL must never receive risk intelligence (band, probability, SHAP,
    # what-changed, recommendations, trust, decision, trajectory).
    if current_user["role"] == "PERSONNEL":
        return PersonnelPredictionResponse(
            assessment_id=assessment_id,
            personnel_id=personnel_id,
            assessed_at=assessed_at,
            status="recorded",
            message="Your voluntary welfare information has been received and will be reviewed privately by a welfare officer.",
        )

    # WELFARE_OFFICER: full result with safe metadata.
    return PredictionResponse(
        assessment_id=assessment_id,
        personnel_id=personnel_id,
        **result,
        data_trust=trust,
        decision_support=decision,
        trajectory=trajectory,
        trajectory_status="derived_from_history" if prior else "single_assessment",
        early_warning=early_warning,
        what_changed=changed,
        welfare_recommendations=_recommendations(result["predicted_band"]),
        derived_outputs=[
            "Trajectory and What Changed are computed from stored assessment history when a personnel_id is supplied.",
            "Early warning and welfare recommendations are auditable platform rules, not additional model predictions.",
            "Data Trust is a deterministic data-quality heuristic, not model confidence; fusion can abstain and request data verification.",
        ],
        assessed_at=assessed_at,
    )


@router.get("/interventions", response_model=list[Intervention])
async def list_interventions(current_user: dict = Depends(require_welfare_officer)) -> list[Intervention]:
    """WELFARE_OFFICER — List intervention records.

    COMMANDER is blocked from individual intervention data.
    """
    docs = await db.interventions.find().sort("created_at", -1).to_list(100)
    return [Intervention(**doc) for doc in docs]


@router.post("/interventions", response_model=Intervention)
async def create_intervention(payload: InterventionCreate, current_user: dict = Depends(require_welfare_officer)) -> Intervention:
    """WELFARE_OFFICER — Create intervention record."""
    doc = payload.model_dump()
    doc.update({"id": str(uuid4()), "created_at": utc_now()})
    await db.interventions.insert_one(doc)
    return Intervention(**doc)


def _demo_raw_records(engineered: dict[str, float], personnel_id: str) -> list[dict[str, Any]]:
    """Construct a 4-week raw-record ladder whose engineered latest week
    reproduces ``engineered`` (the demo profile's displayed feature vector).

    This gives the frontend raw weekly records to submit, so the live analysis
    path exercises the same causal pipeline as production — the 44-feature
    vector is derived server-side, never trusted from the browser.
    """
    static = {name: float(engineered[name]) for name in STATIC_FEATURES}
    week_values: dict[str, list[float]] = {}
    for f in RAW_NUMERIC_FEATURES:
        r3 = float(engineered[f])
        delta = float(engineered[f"{f}__delta_wow"])
        roll4 = float(engineered[f"{f}__roll4_mean"])
        r2 = r3 - delta
        pair = (4.0 * roll4 - r2 - r3) / 2.0
        week_values[f] = [pair, pair, r2, r3]
    records = []
    for week in range(4):
        record = {"personnel_id": personnel_id, "week": week, **static}
        record.update({f: week_values[f][week] for f in RAW_NUMERIC_FEATURES})
        records.append(record)
    return records


def _demo_profiles() -> list[dict[str, Any]]:
    _ensure_engine_ready()
    def signal_profile(severity: float) -> dict[str, float]:
        """Build deterministic, plausible synthetic inputs across model ranges.

        The risk band is never assigned here; it is always produced by the
        uploaded model during demo seeding and live analysis.
        """
        values = {name: 0.0 for name in engine.feature_names}
        values.update({
            "years_of_service": 12.0,
            "hardship_posting_flag": float(severity >= 5),
            "transfer_count_24mo": min(4.0, severity / 2),
            "years_in_current_posting": max(0.2, 7 - severity * 0.6),
            "weekly_duty_hours": 38 + severity * 3.5,
            "weekly_duty_hours__roll4_mean": 38 + severity * 3,
            "weekly_duty_hours__delta_wow": severity * 1.5,
            "night_shift_ratio": min(0.8, 0.08 + severity * 0.06),
            "night_shift_ratio__roll4_mean": min(0.7, 0.08 + severity * 0.05),
            "night_shift_ratio__delta_wow": severity * 0.02,
            "overtime_hours": severity * 1.8,
            "overtime_hours__roll4_mean": severity * 1.5,
            "overtime_hours__delta_wow": severity * 0.7,
            "days_since_last_rest": 1 + severity * 1.1,
            "days_since_last_rest__roll4_mean": 1 + severity * 0.85,
            "days_since_last_rest__delta_wow": severity * 0.4,
            "days_since_last_leave": 10 + severity * 18,
            "days_since_last_leave__roll4_mean": 8 + severity * 15,
            "days_since_last_leave__delta_wow": min(3.0, severity * 0.3),
            "leave_balance": max(0.0, 40 - severity * 4),
            "leave_balance__roll4_mean": max(0.0, 40 - severity * 3.5),
            "leave_balance__delta_wow": -min(4.5, severity * 0.5),
            "wellness_score_self_report": max(1.0, 9.5 - severity * 0.75),
            "wellness_score_self_report__roll4_mean": max(1.5, 9.5 - severity * 0.65),
            "wellness_score_self_report__delta_wow": -severity * 0.25,
            "sleep_quality_score_self_report": max(1.0, 9.5 - severity * 0.7),
            "sleep_quality_score_self_report__roll4_mean": max(1.5, 9.5 - severity * 0.6),
            "sleep_quality_score_self_report__delta_wow": -severity * 0.23,
            "resting_hr_trend_biometric": -1 + severity * 0.45,
            "resting_hr_trend_biometric__roll4_mean": -0.5 + severity * 0.35,
            "resting_hr_trend_biometric__delta_wow": severity * 0.18,
            "sleep_hours_biometric": max(4.5, 8.3 - severity * 0.35),
            "sleep_hours_biometric__roll4_mean": max(5.0, 8.2 - severity * 0.3),
            "sleep_hours_biometric__delta_wow": -severity * 0.12,
        })
        return values
    profiles = [
        {
            "id": "demo-ms-042",
            "name": "Anita Rawat",
            "service_number": "MS-042",
            "rank": "Major",
            "unit": "Northern Support Group",
            "posting": "Ladakh sector",
            "features": signal_profile(8),
            "raw_records": _demo_raw_records(signal_profile(8), "demo-ms-042"),
            "summary": {"wellness": "3.5 / 10 · trending down", "workload": "66 duty hours · elevated", "leave": "8 days available", "deployment": "Hardship posting"},
        },
        {
            "id": "demo-ms-017",
            "name": "Vikram Singh",
            "service_number": "MS-017",
            "rank": "Captain",
            "unit": "Western Logistics Command",
            "posting": "Jaisalmer field base",
            "features": signal_profile(2),
            "raw_records": _demo_raw_records(signal_profile(2), "demo-ms-017"),
            "summary": {"wellness": "8.0 / 10 · stable", "workload": "45 duty hours · stable", "leave": "32 days available", "deployment": "Routine posting"},
        },
        {
            "id": "demo-ms-088",
            "name": "Farah Khan",
            "service_number": "MS-088",
            "rank": "Lieutenant",
            "unit": "Central Communications Unit",
            "posting": "Srinagar operations hub",
            "features": signal_profile(6),
            "raw_records": _demo_raw_records(signal_profile(6), "demo-ms-088"),
            "summary": {"wellness": "5.0 / 10 · mixed signals", "workload": "59 duty hours · rising", "leave": "16 days available", "deployment": "Operational posting"},
        },
    ]
    return profiles


def _demo_history(features: dict[str, float], profile_index: int) -> list[dict[str, float]]:
    snapshots: list[dict[str, float]] = []
    for step in (3, 2, 1):
        snapshot = dict(features)
        snapshot["weekly_duty_hours"] = max(24.0, features["weekly_duty_hours"] - step * (2 + profile_index))
        snapshot["overtime_hours"] = max(0.0, features["overtime_hours"] - step * 2)
        snapshot["days_since_last_rest"] = max(1.0, features["days_since_last_rest"] - step)
        snapshot["wellness_score_self_report"] = min(10.0, features["wellness_score_self_report"] + step * 0.5)
        snapshot["sleep_hours_biometric"] = min(8.5, features["sleep_hours_biometric"] + step * 0.25)
        snapshots.append(snapshot)
    return snapshots


@router.post("/demo/seed", response_model=DemoSeedResponse)
async def seed_demo_data(current_user: dict = Depends(require_welfare_officer)) -> DemoSeedResponse:
    """WELFARE_OFFICER — Seed demo personnel + assessment history.

    Writing is restricted: this endpoint mutates shared collections and is not
    available to PERSONNEL or COMMANDER.
    """
    _ensure_engine_ready()
    profiles = _demo_profiles()
    for profile_index, profile in enumerate(profiles):
        personnel_doc = {key: profile[key] for key in ("id", "name", "service_number", "rank", "unit", "posting")}
        personnel_doc.update({"is_demo_data": True, "created_at": utc_now()})
        await db.personnel.replace_one({"id": profile["id"]}, personnel_doc, upsert=True)
        await db.risk_assessments.delete_many({"personnel_id": profile["id"]})
        history_snapshots = _demo_history(profile["features"], profile_index)
        for history_index, history_features in enumerate(history_snapshots):
            result = engine.predict(history_features)
            trust = _data_trust(history_features)
            decision = _decision_support(result["predicted_band"], trust, "insufficient_history")
            assessed_at = utc_now() - timedelta(days=(3 - history_index) * 7)
            await db.risk_assessments.insert_one({
                "id": f"{profile['id']}-history-{history_index}",
                "personnel_id": profile["id"],
                "assessed_at": assessed_at,
                "date_key": assessed_at.date().isoformat(),
                "features": history_features,
                "is_latest": history_index == len(history_snapshots) - 1,
                "data_trust": trust.model_dump(),
                "decision_support": decision.model_dump(),
                **result,
            })
    return DemoSeedResponse(seeded_count=len(profiles), message="Synthetic DEMO DATA seeded from real model inference")


@router.get("/demo/personnel", response_model=list[DemoPersonnel])
async def list_demo_personnel(current_user: dict = Depends(require_welfare_officer)) -> list[DemoPersonnel]:
    """WELFARE_OFFICER — List demo personnel (synthetic profiles + risk history).

    Task 3C: restricted from PERSONNEL/COMMANDER.  The demo response includes
    the full 44-feature vectors and risk-history bands which are internal
    welfare-officer decision-support material.
    """
    _ensure_engine_ready()
    result: list[DemoPersonnel] = []
    for profile in _demo_profiles():
        history_docs = await db.risk_assessments.find({"personnel_id": profile["id"]}).sort("assessed_at", 1).to_list(20)
        history = [
            {
                "assessed_at": doc["assessed_at"],
                "band": doc["predicted_band"],
                "probability": doc["risk_probability"],
                "trust_score": doc.get("data_trust", {}).get("score"),
                "fusion_state": doc.get("decision_support", {}).get("state"),
            }
            for doc in history_docs
        ]
        result.append(DemoPersonnel(is_demo_data=True, history=history, **profile))
    return result


async def _create_record(collection: str, payload: dict[str, Any], request: Request, current_user: dict) -> RecordResponse:
    """Shared record-creation logic for the four welfare record collections.

    Enforces personnel ownership for the PERSONNEL role (IDOR guard, audited as
    an idor_denial). COMMANDER is blocked by the role gates on each route.
    """
    personnel_id = payload.get("personnel_id")
    if not isinstance(personnel_id, str) or not personnel_id:
        raise HTTPException(status_code=422, detail="personnel_id is required")

    # Enforce personnel ownership for PERSONNEL role.
    # The authenticated user identity binds the personnel_id scope (IDOR guard).
    # The attempt is audited as an idor_denial before the 403 is raised.
    if current_user["role"] == "PERSONNEL":
        if personnel_id != current_user["user_id"]:
            await log_denial(
                "idor_denial",
                request,
                current_user,
                reason="personnel_scope_violation",
                details={"target_personnel_id": personnel_id},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Personnel can only create records for themselves",
            )

    doc = {"id": str(uuid4()), "personnel_id": personnel_id, "created_at": utc_now(), "payload": payload}
    await getattr(db, collection).insert_one(doc)
    return RecordResponse(**doc)


@router.post("/wellness_logs", response_model=RecordResponse)
async def create_wellness_log(payload: dict[str, Any], request: Request, current_user: dict = Depends(require_any_role("PERSONNEL", "WELFARE_OFFICER"))) -> RecordResponse:
    """PERSONNEL (own records only) / WELFARE_OFFICER (any personnel) — Create wellness record.

    COMMANDER is blocked: individual wellness records are inaccessible to the
    Command role in this phase.
    """
    return await _create_record("wellness_logs", payload, request, current_user)


@router.post("/workload_records", response_model=RecordResponse)
async def create_workload_record(payload: dict[str, Any], request: Request, current_user: dict = Depends(require_any_role("PERSONNEL", "WELFARE_OFFICER"))) -> RecordResponse:
    """PERSONNEL (own records only) / WELFARE_OFFICER (any personnel) — Create workload record.

    COMMANDER is blocked: individual workload records are inaccessible to the
    Command role in this phase.
    """
    return await _create_record("workload_records", payload, request, current_user)


@router.post("/deployment_history", response_model=RecordResponse)
async def create_deployment_history(payload: dict[str, Any], request: Request, current_user: dict = Depends(require_any_role("PERSONNEL", "WELFARE_OFFICER"))) -> RecordResponse:
    """PERSONNEL (own records only) / WELFARE_OFFICER (any personnel) — Create deployment record.

    COMMANDER is blocked: individual deployment records are inaccessible to the
    Command role in this phase.
    """
    return await _create_record("deployment_history", payload, request, current_user)


@router.post("/leave_requests", response_model=RecordResponse)
async def create_leave_request(payload: dict[str, Any], request: Request, current_user: dict = Depends(require_any_role("PERSONNEL", "WELFARE_OFFICER"))) -> RecordResponse:
    """PERSONNEL (own records only) / WELFARE_OFFICER (any personnel) — Create leave request.

    COMMANDER is blocked: individual leave records are inaccessible to the
    Command role in this phase.
    """
    return await _create_record("leave_requests", payload, request, current_user)


@router.get("/my/records", response_model=list[PersonnelRecord])
async def my_records(current_user: dict = Depends(require_personnel)) -> list[PersonnelRecord]:
    """PERSONNEL — Read only the authenticated user's own welfare records.

    Task 3C data isolation: the ownership scope is derived from the
    authenticated identity (current_user["user_id"]) and applied directly in
    each database query.  No client-supplied personnel_id or user_id field is
    accepted, so ownership can never be bypassed by request tampering.
    """
    user_id = current_user["user_id"]
    records: list[PersonnelRecord] = []
    for collection in PERSONNEL_RECORD_COLLECTIONS:
        docs = await getattr(db, collection).find({"personnel_id": user_id}).sort("created_at", -1).to_list(100)
        for doc in docs:
            records.append(
                PersonnelRecord(
                    id=doc["id"],
                    collection=collection,
                    created_at=doc["created_at"],
                    payload=doc.get("payload", {}),
                )
            )
    records.sort(key=lambda item: item.created_at, reverse=True)
    return records


@router.get("/my/assessments", response_model=list[PersonnelAssessment])
async def my_assessments(current_user: dict = Depends(require_personnel)) -> list[PersonnelAssessment]:
    """PERSONNEL — Read only the authenticated user's own assessment timestamps.

    Deliberately returns no risk intelligence (no band, probability, SHAP,
    what-changed, recommendations, trust or decision data): only assessment
    identity and when it was recorded.  The query is scoped by authenticated
    identity in the database query itself.
    """
    user_id = current_user["user_id"]
    docs = await db.risk_assessments.find({"personnel_id": user_id}).sort("assessed_at", 1).to_list(100)
    return [PersonnelAssessment(assessment_id=doc["id"], assessed_at=doc["assessed_at"]) for doc in docs]
