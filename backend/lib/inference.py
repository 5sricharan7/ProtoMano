"""Load the uploaded serialized artifacts and run model-backed inference only."""

from __future__ import annotations

import __main__
import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd


def preprocess_for_inference(features: pd.DataFrame) -> np.ndarray:
    """Runtime compatibility hook for the uploaded FunctionTransformer.

    The 273-byte preprocessing pickle stores a reference to this function as
    ``__main__.preprocess_for_inference`` but does not contain its source. The
    model metadata documents an already-engineered 44-column numeric matrix, so
    this adapter preserves the supplied order and removes dataframe labels.
    """

    return features.to_numpy(dtype=float) if hasattr(features, "to_numpy") else np.asarray(features, dtype=float)


class ModelArtifactError(RuntimeError):
    pass


class InferenceEngine:
    def __init__(self, artifact_dir: Path | None = None):
        self.artifact_dir = artifact_dir or Path(
            os.environ.get("MODEL_ARTIFACT_DIR", Path(__file__).resolve().parents[2] / "artifacts")
        )
        self.metadata: dict[str, Any] = {}
        self.risk_model: Any = None
        self.baseline_model: Any = None
        self.preprocessing_pipeline: Any = None
        self.load_error: str | None = None

    @property
    def feature_names(self) -> list[str]:
        return list(self.metadata.get("feature_list_in_order", []))

    @property
    def bands(self) -> list[str]:
        return list(self.metadata.get("band_order", ["Low", "Moderate", "High"]))

    def load(self) -> None:
        try:
            required = [
                "model_metadata.json",
                "risk_model.pkl",
                "preprocessing_pipeline.pkl",
                "baseline_model.pkl",
            ]
            missing = [name for name in required if not (self.artifact_dir / name).exists()]
            if missing:
                raise ModelArtifactError(f"Missing model artifacts: {', '.join(missing)}")
            self.metadata = json.loads((self.artifact_dir / "model_metadata.json").read_text())
            # joblib is required: the model files contain numpy array blocks in
            # the joblib stream format even though their extension is .pkl.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.risk_model = joblib.load(self.artifact_dir / "risk_model.pkl")
                self.baseline_model = joblib.load(self.artifact_dir / "baseline_model.pkl")
                setattr(__main__, "preprocess_for_inference", preprocess_for_inference)
                self.preprocessing_pipeline = joblib.load(self.artifact_dir / "preprocessing_pipeline.pkl")
            if len(self.feature_names) != 44 or getattr(self.risk_model, "n_features_in_", 0) != 44:
                raise ModelArtifactError("Artifact feature metadata and model input width do not match")
            self.load_error = None
        except Exception as exc:
            self.load_error = str(exc)
            raise ModelArtifactError(self.load_error) from exc

    def info(self) -> dict[str, Any]:
        return {
            "product_name": "Manobal-AI",
            "model_version": self.metadata.get("model_version", "unavailable"),
            "feature_version": self.metadata.get("feature_version", "unavailable"),
            "feature_count": len(self.feature_names),
            "feature_list_in_order": self.feature_names,
            "band_order": self.bands,
            "supports_probability": self.risk_model is not None and hasattr(self.risk_model, "predict_proba"),
            "supports_contributions": self.risk_model is not None,
            "preprocessing_status": "runtime_compatibility_adapter",
            "preprocessing_note": "The uploaded FunctionTransformer references __main__.preprocess_for_inference but does not embed its source. Manobal-AI preserves the documented 44-feature order and passes a numeric matrix to the serialized model.",
            "limitations": [
                self.metadata.get("notes", "Synthetic training data; revalidation is required before real deployment."),
                "The model is decision support for voluntary welfare check-ins and human follow-up, never a diagnosis or disciplinary signal.",
                "Trajectory, early-warning status, change summaries and recommendations are derived platform logic, not additional model outputs.",
            ],
        }

    def predict(self, feature_values: dict[str, float]) -> dict[str, Any]:
        if self.load_error or self.risk_model is None or self.preprocessing_pipeline is None:
            raise ModelArtifactError(self.load_error or "Model artifacts are not loaded")
        if set(feature_values) != set(self.feature_names):
            missing = sorted(set(self.feature_names) - set(feature_values))
            extra = sorted(set(feature_values) - set(self.feature_names))
            raise ValueError(f"Feature keys must exactly match metadata; missing={missing}, extra={extra}")
        ordered = pd.DataFrame([[feature_values[name] for name in self.feature_names]], columns=self.feature_names)
        processed = self.preprocessing_pipeline.transform(ordered)
        predicted_index = int(self.risk_model.predict(processed)[0])
        probabilities = np.asarray(self.risk_model.predict_proba(processed)[0], dtype=float)
        band_index = min(max(predicted_index, 0), len(self.bands) - 1)
        predicted_band = self.bands[band_index]

        contributions = self._contributions(processed, band_index)
        return {
            "predicted_band": predicted_band,
            "risk_probability": float(probabilities[band_index]),
            "class_probabilities": [
                {"band": self.bands[index], "probability": float(probabilities[index])}
                for index in range(min(len(self.bands), len(probabilities)))
            ],
            "prediction_confidence": float(np.max(probabilities)),
            "confidence_basis": "Maximum calibrated class probability from risk_model.pkl",
            "top_contributing_factors": contributions,
            "model_version": self.metadata.get("model_version", "unknown"),
            "feature_version": self.metadata.get("feature_version", "unknown"),
        }

    def _contributions(self, processed: Any, predicted_index: int) -> list[dict[str, Any]]:
        try:
            calibrated = self.risk_model.calibrated_classifiers_[0].estimator.estimator
            raw = np.asarray(calibrated.predict(processed, pred_contrib=True))
            width = len(self.feature_names) + 1
            if raw.ndim != 2 or raw.shape[1] < width * len(self.bands):
                return []
            values = raw[0].reshape(len(self.bands), width)[predicted_index, :-1]
            ranked = np.argsort(np.abs(values))[::-1][:5]
            return [
                {
                    "feature": self.feature_names[index],
                    "contribution": float(values[index]),
                    "direction": "increases" if values[index] > 0 else "decreases" if values[index] < 0 else "neutral",
                }
                for index in ranked
            ]
        except Exception:
            # Explainability is optional and never allowed to break inference.
            return []


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
