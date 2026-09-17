"""Task 4C — Welfare prediction orchestration for Welfare Officers.

Bridges the stored 4-week raw welfare window (Task 4B) to the EXISTING
feature-engineering and calibrated-lightGBM inference layers.

This module ONLY orchestrates the existing production components — it contains
no second feature-engineering implementation and no model code:

  raw data        -> lib.history.build_four_week_window          (Task 4B)
  44 features     -> lib.feature_engineering (inside inference)   (unchanged)
  prediction      -> lib.inference.InferenceEngine.model loading  (unchanged)

Missing or incomplete stored data never turns into a fabricated prediction:
the window builder's errors and the feature-engineering contract violations
are mapped to a safe :class:`WelfarePredictionUnavailable` envelope, while
model / artifact failures surface as :class:`lib.inference.ModelArtifactError`.
"""

from __future__ import annotations

from typing import Any

from lib.history import WindowBuilderError, build_four_week_window
from lib.inference import InferenceEngine, ModelArtifactError


class WelfarePredictionUnavailable(ValueError):
    """Raised when a model-backed welfare prediction cannot be produced.

    Carries a safe, stable ``reason`` label plus an officer-readable
    ``message``.  The endpoint converts this into a structured
    :class:`models.welfare.PredictionUnavailable` response — never a
    fabricated prediction.
    """

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason
        self.message = message


async def predict_personnel_welfare(
    personnel_id: str,
    current_user: dict[str, Any],
    engine: InferenceEngine,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, float]]:
    """Produce a model-backed welfare prediction for one personnel.

    Args:
        personnel_id: The personnel record to predict for.  Only data already
            stored for this personnel is ever used.
        current_user: Authenticated identity (``user_id``, ``role``).  The
            Task 4B window builder re-checks the WELFARE_OFFICER role.
        engine: The loaded :class:`InferenceEngine` (inference only; no
            retraining or model replacement happens here).

    Returns:
        ``(window, result, features)``:
        - ``window``: the Task 4B 4-week raw-record envelope.
        - ``result``: the exact calibrated-model prediction dict.
        - ``features``: the 44 ordered feature values the model consumed
          (metadata order); used internally for data-trust heuristics and
          never placed in any API response.

    Raises:
        lib.history.HistoryAccessError: non-WELFARE_OFFICER caller (defense
            in depth).
        WelfarePredictionUnavailable: no usable stored observations, or the
            stored data cannot satisfy the feature-engineering contract.
        ModelArtifactError: model artifacts are missing/unreadable/broken.
    """
    if engine is None:
        raise ModelArtifactError("Model artifacts are not loaded")

    try:
        window = await build_four_week_window(personnel_id, current_user)
    except WindowBuilderError as exc:
        raise WelfarePredictionUnavailable(
            "no_welfare_history",
            "No timestamped welfare observations were found for this personnel; "
            "a model-backed prediction requires at least one recorded observation.",
        ) from exc
    except ValueError as exc:
        raise WelfarePredictionUnavailable(
            "insufficient_data",
            "The stored welfare history for this personnel cannot safely produce "
            "a prediction; no values are fabricated or guessed.",
        ) from exc

    try:
        result, features = engine.predict_from_raw_records(
            window.get("raw_records") or [], personnel_id=personnel_id
        )
    except ModelArtifactError:
        raise
    except ValueError as exc:
        # e.g. static personnel fields are unrecoverable and the raw frame is
        # rejected by the feature-engineering contract.  Never guess values.
        raise WelfarePredictionUnavailable(
            "insufficient_data",
            "The stored welfare history for this personnel is incomplete and "
            "cannot produce the exact features the model requires; no values "
            "are fabricated or guessed.",
        ) from exc

    return window, result, features