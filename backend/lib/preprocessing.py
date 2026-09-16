"""Production preprocessing module for Manobal-AI inference pipeline.

The preprocessing function is imported by the serialized FunctionTransformer
artifact. It must remain stable and importable from a clean Python process.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def preprocess_for_inference(features: pd.DataFrame) -> np.ndarray:
    """Convert the 44-feature DataFrame to a numeric matrix for LightGBM.

    The model expects exactly 44 numeric features in the order documented by
    artifacts/model_metadata.json. All feature engineering (rolling windows,
    deltas, missingness flags) is already complete when this function runs.

    This function preserves the supplied column order and converts the
    DataFrame to a numpy array that the calibrated LightGBM model consumes.

    Args:
        features: DataFrame with 44 columns matching model_metadata feature order

    Returns:
        2D numpy array of shape (n_samples, 44) with dtype float64
    """
    return features.to_numpy(dtype=float) if hasattr(features, "to_numpy") else np.asarray(features, dtype=float)
