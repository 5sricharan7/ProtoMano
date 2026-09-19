"""Task 4D — Welfare risk trajectory and early-warning layer for Welfare Officers.

Sits on top of the Task 4C prediction service
(:func:`lib.welfare_prediction.predict_personnel_welfare`) and the STORED
assessment history to classify a personnel's risk trajectory and emit auditable
temporal early-warning signals.  It contains no model code and no
feature-engineering logic — it only READS the calibrated model's outputs
(``predicted_band``, ``risk_probability``, ``class_probabilities``).

Trend semantics:

- A risk point's trend signal is the model's **High-class probability** from
  ``class_probabilities`` — the only output that is monotonic with risk across
  band transitions (e.g. a Low->High transition always raises it, a High->Low
  transition always lowers it).  ``risk_probability`` is the *predicted-band*
  probability and would mislabel easing as rising across band transitions, so
  it is never used directly as the trend signal.
- Direction is computed from the TWO NEWEST chronologically ordered points with
  the same 1e-9 materiality epsilon the existing /predict trajectory logic uses.
- Missing temporal evidence never invents a trend: fewer than two chronological
  points yields ``insufficient_data``, never a fabricated direction.

Early-warning semantics (temporal only):

- Early warnings REQUIRE at least two chronologically ordered assessments.  A
  single assessment — even a High one — can never raise a warning (a
  single-point band is visible in the prediction snapshot, but it is not a
  *trajectory* warning).  This is a deliberate, documented deviation from the
  band-first ``_early_warning`` used by /predict: Task 4D early warnings are
  trajectory signals, and fabricating one from missing temporal evidence would
  be a false alarm.
- ``human_review``: the two newest chronological points are BOTH High — a
  sustained high-risk condition.
- ``watch``: risk is rising (increasing High-class probability).  Also covers
  one-off deterioration from a low baseline.
- ``not_available``: easing, stable, or insufficient temporal evidence.

Causal / no-future-leakage rules:

- The current prediction point is the live run; its ``assessed_at`` is the run
  time (server UTC clock).
- Stored assessments dated AFTER the current run time are EXCLUDED from the
  trajectory (a causal cut-off): a record stamped in the future could not have
  influenced or preceded the current signal and must never flip the trend.
- Only a personnel's OWN stored assessments are read; stored snapshots returned
  to the officer carry band + probability only (never the 44-feature vector).

The layer re-checks the WELFARE_OFFICER role through the Task 4B window builder
(defense in depth), exactly like Task 4C.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from lib.db import db
from lib.inference import InferenceEngine, utc_now
from lib.welfare_prediction import predict_personnel_welfare

# Same materiality epsilon the /predict trajectory direction classifier uses.
PREDICTION_EPSILON = 1e-9

# How many of the NEWEST stored assessments feed the trajectory/history window.
MAX_HISTORY_POINTS = 20

_STORED_SNAPSHOT_KEYS = ("assessed_at", "predicted_band", "risk_probability")


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


def _chronology_key(point: dict[str, Any]) -> tuple[float, str]:
    """Deterministic ascending key: timestamp, then point id (ties break by id)."""
    value = _coerce_datetime(point.get("assessed_at")) or datetime.min.replace(tzinfo=timezone.utc)
    return (value.timestamp(), str(point.get("id", "")))


def _risk_signal(point: dict[str, Any]) -> float:
    """High-class probability as the monotonic-with-risk trend signal.

    Prefers the model's ``class_probabilities`` (always present on documents
    written by the canonical pipeline).  Defensive conservative fallback for
    documents that lack it: the High-band confidence is recovered only when the
    predicted band is High, otherwise the signal is 0.0 (no High-risk evidence).
    The fallback can only UNDER-state risk for legacy documents — it can never
    fabricate deterioration.
    """
    class_probs = point.get("class_probabilities")
    if class_probs:
        try:
            for entry in class_probs:
                if entry.get("band") == "High":
                    return float(entry.get("probability", 0.0) or 0.0)
        except (TypeError, AttributeError):
            return 0.0
        return 0.0
    if point.get("predicted_band") == "High":
        try:
            return float(point.get("risk_probability", 0.0) or 0.0)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def classify_trajectory(points: list[dict[str, Any]]) -> str:
    """Classify the risk trajectory from the two newest chronological points.

    Labels: ``increasing`` / ``decreasing`` / ``stable`` / ``insufficient_data``.

    ``points`` entries carry ``assessed_at`` plus either ``class_probabilities``
    or ``predicted_band`` + ``risk_probability``.  Points without a usable
    ``assessed_at`` are ignored (never guessed); fewer than two usable points
    is ``insufficient_data`` (never a fabricated direction).
    """
    valid = sorted(
        (point for point in points if _coerce_datetime(point.get("assessed_at")) is not None),
        key=_chronology_key,
    )
    if len(valid) < 2:
        return "insufficient_data"
    previous = _risk_signal(valid[-2])
    current = _risk_signal(valid[-1])
    if current > previous + PREDICTION_EPSILON:
        return "increasing"
    if current < previous - PREDICTION_EPSILON:
        return "decreasing"
    return "stable"


def build_early_warning(points: list[dict[str, Any]]) -> dict[str, str]:
    """Temporal early-warning signal over the chronological point sequence.

    Never fires from a single point or missing temporal evidence: a warning
    requires at least two assessments.  ``human_review`` for a sustained
    (two consecutive) High band; ``watch`` for rising risk; otherwise
    ``not_available``.
    """
    valid = sorted(
        (point for point in points if _coerce_datetime(point.get("assessed_at")) is not None),
        key=_chronology_key,
    )
    if len(valid) < 2:
        return {
            "status": "not_available",
            "label": "No trajectory signal",
            "basis": (
                "An early warning requires at least two chronologically ordered "
                "assessments; no warning is issued from a single assessment or "
                "missing temporal evidence."
            ),
        }
    previous = valid[-2]
    current = valid[-1]
    if previous.get("predicted_band") == "High" and current.get("predicted_band") == "High":
        return {
            "status": "human_review",
            "label": "Sustained high risk",
            "basis": (
                "The two newest chronologically ordered assessments both show a "
                "High risk band; sustained High risk warrants prompt human welfare review."
            ),
        }
    direction = classify_trajectory(valid)
    if direction == "increasing":
        return {
            "status": "watch",
            "label": "Watch rising trajectory",
            "basis": (
                "The two newest chronologically ordered assessments show rising "
                "risk (High-class probability); the risk trajectory is deteriorating."
            ),
        }
    if direction == "decreasing":
        return {
            "status": "not_available",
            "label": "Risk level easing",
            "basis": (
                "The two newest chronologically ordered assessments show falling "
                "risk (High-class probability); the risk trajectory is easing."
            ),
        }
    return {
        "status": "not_available",
        "label": "Risk level stable",
        "basis": (
            "The two newest chronologically ordered assessments show no material "
            "risk change (within the 1e-9 materiality epsilon)."
        ),
    }


def _minimize_snapshot(point: dict[str, Any]) -> dict[str, Any]:
    return {key: point[key] for key in _STORED_SNAPSHOT_KEYS if key in point}


async def build_personnel_trajectory(
    personnel_id: str,
    current_user: dict[str, Any] | None,
    engine: InferenceEngine,
) -> dict[str, Any]:
    """Build the welfare risk trajectory for ONE personnel.

    Flow: Task 4C prediction (stored window -> canonical features -> model) plus
    the stored assessment confirmation history, appended as one chronological
    sequence with a causal cut-off that excludes any stored assessment dated
    after the current run.

    Returns:
        A response-ready envelope (``personnel_id``, ``trend``,
        ``early_warning``, ``history``, ``prediction``, ``evidence_basis``,
        ``assessed_at``, ``derived_outputs``).

    Raises:
        lib.history.HistoryAccessError: non-WELFARE_OFFICER caller.
        WelfarePredictionUnavailable: no model-backed prediction possible.
        ModelArtifactError: model artifacts are broken/missing.
    """
    run_at = utc_now()

    # Task 4C already re-checks the WELFARE_OFFICER role (defense in depth) and
    # raises WelfarePredictionUnavailable when no prediction is possible.
    _, result, _ = await predict_personnel_welfare(personnel_id, current_user, engine)

    # Newest 20 stored assessments first (reverse-chronological), then re-sorted
    # ascending so the response history is chronological and the classification
    # sees the truly NEWEST points even when more than 20 exist.
    stored_docs = await db.risk_assessments.find({"personnel_id": personnel_id}).sort(
        "assessed_at", -1
    ).to_list(MAX_HISTORY_POINTS)

    history: list[dict[str, Any]] = []
    for doc in stored_docs:
        stored_at = _coerce_datetime(doc.get("assessed_at"))
        if stored_at is None:
            # No usable timestamp: placing it would mean guessing chronology.
            continue
        if stored_at > run_at:
            # Causal cut-off: a future-dated stored assessment cannot precede
            # (or have influenced) the current signal.  Never used.
            continue
        history.append({
            "id": str(doc.get("id", "")),
            "assessed_at": doc.get("assessed_at"),
            "predicted_band": doc.get("predicted_band"),
            "risk_probability": float(doc.get("risk_probability", 0.0)),
            "class_probabilities": doc.get("class_probabilities", []),
        })
    history.sort(key=_chronology_key)

    current_point = {
        "assessed_at": run_at,
        "predicted_band": result["predicted_band"],
        "risk_probability": float(result["risk_probability"]),
        "class_probabilities": result["class_probabilities"],
        "id": "current",
    }

    points = history + [current_point]
    trend = classify_trajectory(points)
    early_warning = build_early_warning(points)

    return {
        "personnel_id": personnel_id,
        "trend": trend,
        "early_warning": early_warning,
        "history": [_minimize_snapshot(point) for point in history],
        "prediction": _minimize_snapshot(current_point),
        "evidence_basis": (
            "The risk trajectory compares the two newest chronologically ordered "
            "assessments (stored confirmation history plus this live prediction) "
            "on the calibrated model's High-class probability with a 1e-9 "
            "materiality epsilon.  Stored assessments dated after the current "
            "run time are excluded by a causal cut-off; they could not have "
            "preceded the current signal."
        ),
        "assessed_at": run_at,
        "derived_outputs": [
            "The risk trajectory and early warning are auditable platform rules over the calibrated model's band/probability outputs — not additional model predictions.",
            "Early warnings are temporal signals: they require at least two chronologically ordered assessments; a single assessment or missing history can never raise one.",
            "Stored history snapshots are minimized to band and probability only; the 44-feature vector is never returned.",
        ],
    }