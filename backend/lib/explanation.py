"""Task 4E — Explainable welfare AI for Welfare Officers.

Decision-support explainability on top of the EXISTING Task 4C prediction
service.  This module ONLY reads the deployed calibrated model's outputs and the
existing canonical feature vectors; it never retrains, replaces or re-derives
the model, never writes model artifacts, and never exposes the raw 44-feature
vector, model filenames, artifact paths, credentials or internal implementation
details.

Explainability method (SHAP decision):

The external SHAP library is NOT part of the deployed runtime (it is absent from
``backend/requirements.txt`` and not importable in the current environment), and
the deployed artifact is a CALIBRATED multiclass LightGBM classifier whose public
probabilities differ from raw tree margins.  Safely attributing the *calibrated*
risk signal with SHAP would require a separate non-approximating attribution
setup that this artifact/environment does not provide.  Per the Task 4E policy,
SHAP is therefore NOT used and is NOT claimed.  Instead this layer reuses the
deployed model's NATIVE additive feature contributions (``pred_contrib=True``) —
the exact values the existing ``lib.inference.InferenceEngine`` already surfaces
as ``top_contributing_factors``.  These are derived directly from the existing
model/inference behavior, use the model's real feature names/order, and are
clearly labeled as ``native_feature_contributions``, never as SHAP.

``shap_availability()`` is a pure *probe* used by tests/operators to confirm the
documented fallback situation; a positive probe never changes the method used.

What Changed?  (temporal explainability)

``build_what_changed`` compares the current engineered vector (the exact values
the model consumed) against the newest chronologically prior piece of temporal
evidence:

1. The newest STORED assessment that carries the full feature snapshot and is
   dated at or before the current run (causal cut-off: a future-dated stored
   assessment can never influence the comparison).
2. Otherwise, the prior OBSERVED week inside the Task 4B 4-week raw window,
   re-engineered through the existing canonical pipeline (the window's own
   temporal evidence).

Missing data is NEVER reported as improvement or deterioration: a factor is
included in a change only when it was OBSERVED in BOTH the current and the prior
period (both ``__was_missing`` indicators 0).  Deltas below a relative
materiality threshold are not reported.  If no usable prior temporal evidence
exists, a structured ``insufficient_data`` result is returned instead of
guessing.  Never creates future values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib.db import db
from lib.feature_engineering import (
    RAW_NUMERIC_FEATURES,
    STATIC_FEATURES,
    engineer_features,
    get_feature_columns,
    records_to_frame,
)
from lib.inference import InferenceEngine, utc_now
from lib.welfare_prediction import predict_personnel_welfare

# Explainability method label used throughout the response surface.  This is the
# deployed model's native additive contribution output — never the external SHAP
# library, which is not part of the runtime and is not claimed.
EXPLANATION_METHOD = "native_feature_contributions"

# Relative materiality: a change must exceed this fraction of the observed scale
# (max absolute magnitude of the two values, floored at 1.0) to be reported.
CHANGE_MATERIALITY = 1e-6

# How many of the largest absolute changes are included in the What Changed list.
MAX_CHANGES = 5

_MISSING_SUFFIX = "__was_missing"

_STATIC_DISPLAY = {
    "years_of_service": "Years of service",
    "hardship_posting_flag": "Hardship posting",
    "transfer_count_24mo": "Transfers in last 24 months",
    "years_in_current_posting": "Years in current posting",
}

_RAW_DISPLAY = {
    "weekly_duty_hours": "Weekly duty hours",
    "night_shift_ratio": "Night shift ratio",
    "overtime_hours": "Overtime hours",
    "days_since_last_rest": "Days since last rest",
    "days_since_last_leave": "Days since last leave",
    "leave_balance": "Leave balance",
    "wellness_score_self_report": "Self-reported wellness score",
    "sleep_quality_score_self_report": "Self-reported sleep quality score",
    "resting_hr_trend_biometric": "Resting heart-rate trend",
    "sleep_hours_biometric": "Biometric sleep hours",
}

_RAW_VARIANT_DISPLAY = {
    "roll4_mean": " (4-week average)",
    "delta_wow": " (week-over-week change)",
    "was_missing": " (missing indicator)",
}


def shap_availability() -> dict[str, Any]:
    """Probe whether the external SHAP library is importable.

    Availability probe only: the explanation layer never substitutes SHAP for the
    deployed calibrated-LightGBM artifact's native contributions, with or without
    this probe, so the probe is informational and used by tests/operators to
    confirm the documented fallback situation.  A positive probe never changes
    the method used and the response never claims SHAP.
    """
    try:
        import shap  # type: ignore[import-not-found]
    except Exception:
        return {"available": False, "version": None}
    return {"available": True, "version": getattr(shap, "__version__", "unknown")}


def display_name(feature: str) -> str:
    """Officer-readable label for one public model factor name.

    Falls back to the public metadata name itself for any unrecognized factor,
    so a label is never invented.  Internal engineered variants are rendered as
    friendly text (no ``__`` tokens surface to the officer).
    """
    base, sep, variant = feature.partition("__")
    if not sep:
        return _STATIC_DISPLAY.get(base, _RAW_DISPLAY.get(base, base))
    if variant in _RAW_VARIANT_DISPLAY:
        return _RAW_DISPLAY.get(base, base) + _RAW_VARIANT_DISPLAY[variant]
    return feature


def _impact_summary(direction: str) -> str:
    if direction == "increases":
        return "contributes to raising the risk signal"
    if direction == "decreases":
        return "contributes to reducing the risk signal"
    return "no clear directional contribution"


def _contribution_direction_map(result: dict[str, Any]) -> dict[str, str]:
    directions: dict[str, str] = {}
    for item in result.get("top_contributing_factors", []):
        if isinstance(item, dict) and isinstance(item.get("feature"), str):
            directions[item["feature"]] = str(item.get("direction", "neutral"))
    return directions


def build_top_factors(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Officer-facing top contributing factors with friendly display labels.

    Reuses the model's native contribution output from the Task 4C result; no
    prediction logic is duplicated and nothing is re-approximated.
    """
    factors: list[dict[str, Any]] = []
    for item in result.get("top_contributing_factors", []):
        if not isinstance(item, dict):
            continue
        feature = item.get("feature")
        if not isinstance(feature, str):
            continue
        direction = str(item.get("direction", "neutral"))
        factors.append({
            "feature": feature,
            "display_name": display_name(feature),
            "contribution": float(item.get("contribution", 0.0)),
            "direction": direction,
            "impact_summary": _impact_summary(direction),
        })
    return factors


def _coerce_datetime(value: Any) -> datetime | None:
    """Normalize a stored timestamp to a timezone-aware datetime (UTC)."""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed
    return None


def _observed(features: dict[str, Any], feature: str) -> bool:
    """True only when the factor was genuinely observed in ``features``.

    Static factors are required by the engineering contract and are never
    missing.  For the raw-weekly family, an absent ``__was_missing`` flag means
    the observation status is unconfirmed and the factor is treated as NOT
    observed (safer: excluded, never fabricated).
    """
    if feature in STATIC_FEATURES:
        return True
    base = feature.split("__", 1)[0]
    flag = f"{base}{_MISSING_SUFFIX}"
    if flag not in features:
        return False
    try:
        return int(features[flag]) == 0
    except (TypeError, ValueError):
        return False


def _change_impact(direction: str, delta: float) -> str:
    """Model-implied consequence of a change, only when reliably known.

    Combines the CURRENT model's native contribution direction for the exact
    factor with the observed delta sign.  Factors whose individual direction is
    not among the surfaced native contributions report ``unknown`` (never
    guessed).  It describes movement of the model's risk signal — decision
    support, not an assessment.
    """
    if direction not in ("increases", "decreases"):
        return "unknown"
    if delta == 0:
        return "unknown"
    pushes_higher = (direction == "increases" and delta > 0) or (
        direction == "decreases" and delta < 0
    )
    return "increases_risk_signal" if pushes_higher else "decreases_risk_signal"


def build_change_items(
    current: dict[str, Any],
    prior: dict[str, Any],
    directions: dict[str, str],
) -> list[dict[str, Any]]:
    """Rank observable current-vs-prior changes for the What Changed list.

    Rules:
    - Only factors OBSERVED in both periods are considered (missing data is
      never reported as improvement or deterioration).
    - Missingness indicators themselves are never listed as changes.
    - Deltas below the relative materiality threshold are not reported.
    - Deterministic ordering: largest absolute delta first, ties by factor name.
    """
    entries: list[dict[str, Any]] = []
    for name in current:
        if not isinstance(name, str) or name.endswith(_MISSING_SUFFIX):
            continue
        if name not in prior:
            continue
        try:
            current_value = float(current[name])
            prior_value = float(prior[name])
        except (TypeError, ValueError):
            continue
        if not (_observed(current, name) and _observed(prior, name)):
            continue
        delta = current_value - prior_value
        scale = max(abs(current_value), abs(prior_value), 1.0)
        if abs(delta) <= CHANGE_MATERIALITY * scale:
            continue
        direction = directions.get(name, "unknown")
        entries.append({
            "feature": name,
            "display_name": display_name(name),
            "previous": prior_value,
            "current": current_value,
            "delta": delta,
            "change": "increased" if delta > 0 else "decreased",
            "contribution_direction": direction,
            "impact": _change_impact(direction, delta),
        })
    entries.sort(key=lambda item: (-abs(item["delta"]), item["feature"]))
    return entries[:MAX_CHANGES]


async def _newest_prior_stored(personnel_id: str, run_at: datetime) -> dict[str, Any] | None:
    """Newest stored feature snapshot dated at or before ``run_at``.

    Applies a causal cut-off: a stored assessment dated after the current run
    could not have preceded or influenced the current signal and is excluded.
    Returns the newest eligible snapshot's feature vector, or None.
    """
    docs = await db.risk_assessments.find({"personnel_id": personnel_id}).to_list(200)
    eligible: list[tuple[datetime, dict[str, Any]]] = []
    for doc in docs:
        stored_at = _coerce_datetime(doc.get("assessed_at"))
        if stored_at is None or stored_at > run_at:
            continue
        snapshot = doc.get("features")
        if isinstance(snapshot, dict) and snapshot:
            eligible.append((stored_at, snapshot))
    if not eligible:
        return None
    eligible.sort(key=lambda pair: pair[0].timestamp())
    return eligible[-1][1]


def _window_prior_week(window: dict[str, Any]) -> dict[str, Any] | None:
    """Prior OBSERVED week of the 4-week raw window, re-engineered canonically.

    Derives the engineered rows for every window week through the EXISTING
    canonical pipeline and returns the second-newest week that actually carried
    observed raw numeric values.  Weeks with no observed raw values (fully
    missing) are never used as a comparison baseline.  Returns None when fewer
    than two observed weeks exist.
    """
    raw_records = window.get("raw_records")
    if not raw_records:
        return None
    try:
        frame = records_to_frame(raw_records)
    except ValueError:
        return None
    try:
        engineered = engineer_features(frame)
    except Exception:
        return None
    rows = engineered.sort_values(["personnel_id", "week"]).reset_index(drop=True)
    observed: list[Any] = []
    for _index, row in rows.iterrows():
        if any(int(row[f"{feature}__was_missing"]) == 0 for feature in RAW_NUMERIC_FEATURES):
            observed.append(row)
    if len(observed) < 2:
        return None
    prior_row = observed[-2]
    columns = get_feature_columns()
    return {name: float(prior_row[name]) for name in columns if name in prior_row}


async def build_what_changed(
    personnel_id: str,
    current_features: dict[str, Any],
    window: dict[str, Any],
    run_at: datetime,
    directions: dict[str, str],
) -> dict[str, Any]:
    """Temporal 'What Changed?' over the available causal evidence.

    Priority for the prior baseline: newest stored feature snapshot dated at or
    before the run; otherwise the prior observed window week.  Missing data is
    never reported as improvement or deterioration; insufficient temporal
    evidence yields a structured ``insufficient_data`` envelope.
    """
    stored_prior = await _newest_prior_stored(personnel_id, run_at)
    if stored_prior is not None:
        prior = stored_prior
        comparison = "prior_assessment"
        comparison_basis = (
            "compared against the newest chronologically prior stored assessment "
            "dated at or before this run (causal cut-off — future-dated records "
            "are excluded)"
        )
    else:
        prior = _window_prior_week(window)
        comparison = "prior_week" if prior is not None else None
        comparison_basis = (
            "compared against the prior observed week in the 4-week window, "
            "re-derived through the canonical engineering pipeline"
        ) if prior is not None else None

    if prior is None or comparison is None:
        return {
            "status": "insufficient_data",
            "comparison": None,
            "basis": (
                "No usable prior temporal evidence exists for this personnel — no stored "
                "feature snapshot dated at or before this run and no earlier observed week "
                "in the 4-week window.  Nothing is invented; change cannot be established."
            ),
            "no_material_change": False,
            "changes": [],
        }

    entries = build_change_items(current_features, prior, directions)
    if not entries:
        overlap = [
            name
            for name in current_features
            if name in prior
            and not name.endswith(_MISSING_SUFFIX)
            and _observed(current_features, name)
            and _observed(prior, name)
        ]
        if not overlap:
            return {
                "status": "insufficient_data",
                "comparison": comparison,
                "basis": (
                    f"No factor was observed in both the current and the prior period "
                    f"({comparison_basis}); no change can be reported and missing data is "
                    "never shown as improvement or deterioration."
                ),
                "no_material_change": False,
                "changes": [],
            }
        return {
            "status": "available",
            "comparison": comparison,
            "basis": (
                f"No material change was found ({comparison_basis}) — every compared "
                "factor stayed within the relative materiality threshold."
            ),
            "no_material_change": True,
            "changes": [],
        }

    return {
        "status": "available",
        "comparison": comparison,
        "basis": (
            f"Current-vs-prior changes ranked by magnitude ({comparison_basis}); only "
            "factors observed in both periods are reported, and missing data is never "
            "treated as improvement or deterioration."
        ),
        "no_material_change": False,
        "changes": entries,
    }


async def build_welfare_explanation(
    personnel_id: str,
    current_user: dict[str, Any],
    engine: InferenceEngine,
) -> dict[str, Any]:
    """Build the sanitized welfare explanation for ONE personnel.

    Reuses the existing Task 4C prediction service (stored window -> canonical
    44-feature engineering -> calibrated LightGBM) and the existing Task 4B
    window for temporal evidence.  No second feature-engineering pipeline, no
    model modification, no retraining.

    Returns a response-ready envelope (``personnel_id``, ``explanation_status``,
    ``status_message``, ``prediction``, ``explanation_method``,
    ``top_contributing_factors``, ``what_changed``, ``evidence_basis``,
    ``derived_outputs``, ``assessed_at``).

    Raises:
        lib.history.HistoryAccessError: non-WELFARE_OFFICER caller (defense in
            depth, via the Task 4C service).
        WelfarePredictionUnavailable: no model-backed prediction possible.
        ModelArtifactError: model artifacts are broken/missing.
    """
    run_at = utc_now()
    window, result, features = await predict_personnel_welfare(
        personnel_id, current_user, engine
    )

    factors = build_top_factors(result)
    directions = _contribution_direction_map(result)
    what_changed = await build_what_changed(
        personnel_id, features, window, run_at, directions
    )

    if factors:
        status = "available"
        status_message = (
            "An explanation of the current welfare risk signal is available as "
            "decision-support information for the welfare officer."
        )
        contribution_basis = (
            "Top contributing factors reuse the deployed model's native additive "
            "contribution values for the exact predicted band."
        )
    else:
        status = "explanation_unavailable"
        status_message = (
            "The model prediction is available, but per-factor contribution details "
            "cannot be produced for this artifact; the risk signal itself is unchanged."
        )
        contribution_basis = (
            "Per-factor contribution details are not available for this artifact; "
            "no contribution values are approximated or invented."
        )

    evidence_basis = (
        "The risk signal is produced by the existing deployed calibrated model over the "
        "exact 44 input signals derived server-side from the stored 4-week raw window "
        "by the canonical engineering pipeline; nothing was retrained or re-derived. "
        f"{contribution_basis} ({EXPLANATION_METHOD}; the external attribution library "
        "is not used and this output is not claimed to come from it). "
        f"What Changed: {what_changed['basis']}"
    )

    return {
        "personnel_id": personnel_id,
        "explanation_status": status,
        "status_message": status_message,
        "prediction": {
            "predicted_band": result["predicted_band"],
            "risk_probability": float(result["risk_probability"]),
        },
        "explanation_method": EXPLANATION_METHOD,
        "top_contributing_factors": factors,
        "what_changed": what_changed,
        "evidence_basis": evidence_basis,
        "derived_outputs": [
            "This explanation is decision-support information, not a diagnosis; the model is not a medical or diagnostic tool.",
            "Per-factor contributions come from the deployed model's native additive contribution output and are never claimed to come from an external attribution library.",
            "What Changed compares only factors observed in both the current and prior periods; missing data is never reported as improvement or deterioration.",
            "No future data is used: stored assessments dated after this run are excluded by a causal cut-off, and only the personnel's own records are ever read.",
        ],
        "assessed_at": run_at,
    }