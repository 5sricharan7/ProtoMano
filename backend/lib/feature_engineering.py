"""Canonical raw-record -> 44-feature engineering pipeline for Manobal-AI.

This module is the behavioral source of truth for feature engineering. It is
vendored from the recovered original development notebook
``AI_Personnel_Welfare_Risk_SIH_FINAL(3).ipynb`` (the ``feature_engineering.py``
cell). Do NOT approximate or re-derive these formulas: the exact causal
ordering below is part of the model contract and matches
``artifacts/model_metadata.json``.

Pipeline order (fixed):
  1. sort by [personnel_id, week]
  2. missingness indicators BEFORE any imputation
  3. causal per-person expanding-mean imputation (includes current week)
     -> global-median fallback -> 0.0 final fallback
  4. per-person rolling(window=4, min_periods=1) mean
  5. per-person week-over-week diff(1), first row filled with 0.0
  6. hardship_posting_flag cast to int
  7. final column order: static features first, then for every raw numeric
     feature: raw, __roll4_mean, __delta_wow, __was_missing (EXACTLY 44)

Leakage rule: every engineered feature for week ``w`` uses only data from
weeks <= w for that person. Never a future week.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ROLLING_WINDOW = 4

RAW_NUMERIC_FEATURES = [
    "weekly_duty_hours",
    "night_shift_ratio",
    "overtime_hours",
    "days_since_last_rest",
    "days_since_last_leave",
    "leave_balance",
    "wellness_score_self_report",
    "sleep_quality_score_self_report",
    "resting_hr_trend_biometric",
    "sleep_hours_biometric",
]

STATIC_FEATURES = [
    "years_of_service",
    "hardship_posting_flag",
    "transfer_count_24mo",
    "years_in_current_posting",
]

# Columns a raw record must carry. Raw numeric fields may be null/NaN to
# exercise the causal imputation path; static fields are required and finite.
REQUIRED_RAW_COLUMNS = ["personnel_id", "week"] + STATIC_FEATURES + RAW_NUMERIC_FEATURES

# Authoritative: 4 static + 10 raw * 4 (raw, roll4, delta, was_missing) = exactly 44
FEATURE_COUNT = len(STATIC_FEATURES) + len(RAW_NUMERIC_FEATURES) * 4


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Turns raw weekly records into model-ready engineered features.

    ``df`` needs at least ``personnel_id``, ``week``, the static features and
    the raw numeric features. Returns a new DataFrame (input is not mutated)
    with the engineered columns appended. Sorting is by [personnel_id, week]
    ascending, so every window aggregates only the current and past weeks —
    never a future week.
    """
    df = df.sort_values(["personnel_id", "week"]).reset_index(drop=True).copy()

    # missingness indicators BEFORE any imputation
    for f in RAW_NUMERIC_FEATURES:
        df[f"{f}__was_missing"] = df[f].isna().astype(int)

    grouped = df.groupby("personnel_id", sort=False)

    # Impute raw NaNs FIRST, causally: each person's own expanding mean up to
    # and including that week (never a future week), falling back to the
    # global median only when a person has no prior observed value at all.
    # This ordering matters: rolling/delta features below are then computed
    # on the already-imputed (but still causal) series, so the stored
    # roll4_mean / delta_wow values are reproducible by a manual recomputation
    # on the final df[f] column (see the original leakage audit).
    for f in RAW_NUMERIC_FEATURES:
        expanding_mean = grouped[f].transform(lambda s: s.expanding(min_periods=1).mean())
        df[f] = df[f].fillna(expanding_mean)
        global_median = df[f].median()
        df[f] = df[f].fillna(global_median)
        # Last-resort fallback: if a field is missing for EVERY row (e.g. a
        # cohort with zero opt-in for a given sensor), the global median is
        # itself NaN. Fall back to 0.0 rather than leaving a NaN in the
        # feature matrix — the __was_missing indicator already tells the
        # model this value carries no real signal.
        df[f] = df[f].fillna(0.0)

    grouped = df.groupby("personnel_id", sort=False)  # re-group post-imputation

    for f in RAW_NUMERIC_FEATURES:
        # rolling(window).mean() at row w only includes rows up to and
        # including w — never future rows — because the frame is time-sorted
        # within each group.
        df[f"{f}__roll4_mean"] = grouped[f].transform(
            lambda s: s.rolling(window=ROLLING_WINDOW, min_periods=1).mean()
        )
        df[f"{f}__delta_wow"] = grouped[f].transform(lambda s: s.diff(1)).fillna(0.0)

    df["hardship_posting_flag"] = df["hardship_posting_flag"].astype(int)

    return df


def get_feature_columns() -> list[str]:
    """Exact 44-feature order: static features first, then for each raw
    numeric feature: raw, roll4_mean, delta_wow, was_missing."""
    cols = list(STATIC_FEATURES)
    for f in RAW_NUMERIC_FEATURES:
        cols.append(f)
        cols.append(f"{f}__roll4_mean")
        cols.append(f"{f}__delta_wow")
        cols.append(f"{f}__was_missing")
    return cols


def records_to_frame(records: list[dict] | pd.DataFrame) -> pd.DataFrame:
    """Build and validate a raw-record DataFrame.

    Stands in front of the inference entry point: only the documented raw
    columns are accepted (extra/engineered keys are rejected), static fields
    must be finite, ``week`` must be numeric, and raw numeric fields may be
    null to drive the causal imputation path.

    Accepts a list of record dicts or an already-built DataFrame.

    Raises:
        ValueError: descriptive message for any schema violation.
    """
    frame = records if isinstance(records, pd.DataFrame) else pd.DataFrame(records)
    if frame.empty:
        raise ValueError("raw_records must contain at least one weekly record")

    missing = [col for col in REQUIRED_RAW_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"raw_records missing required columns: {missing}")

    extra = sorted(set(frame.columns) - set(REQUIRED_RAW_COLUMNS))
    if extra:
        raise ValueError(f"raw_records contains unexpected columns: {extra}")

    if frame["personnel_id"].isna().any() or (frame["personnel_id"].astype(str).str.strip() == "").any():
        raise ValueError("raw_records personnel_id must be a non-empty string")

    try:
        frame["week"] = pd.to_numeric(frame["week"], errors="raise")
    except (ValueError, TypeError) as exc:
        raise ValueError("raw_records 'week' must be numeric") from exc

    for col in STATIC_FEATURES:
        non_null = frame[col].notna()
        if not non_null.all():
            raise ValueError(f"raw_records static column '{col}' cannot be missing")
        try:
            pd.to_numeric(frame.loc[non_null, col], errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError(f"raw_records static column '{col}' must be numeric") from exc

    for col in RAW_NUMERIC_FEATURES:
        present = frame[col].notna()
        if present.any():
            try:
                pd.to_numeric(frame.loc[present, col], errors="raise")
            except (ValueError, TypeError) as exc:
                raise ValueError(f"raw_records column '{col}' must be numeric or null") from exc

    return frame


def features_for_latest_week(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Controlled raw-record -> 44-feature entry point for inference.

    Returns one row per distinct ``personnel_id`` holding the EXACT 44 ordered
    features for that person's latest (maximum) week. These rows are what the
    model consumes, in ``get_feature_columns()`` order.
    """
    engineered = engineer_features(raw_df)
    latest = (
        engineered.sort_values("week")
        .groupby("personnel_id", sort=False, as_index=False)
        .tail(1)
    )
    return latest[["personnel_id"] + get_feature_columns()].reset_index(drop=True)


def preprocess_for_inference(raw_df: pd.DataFrame) -> np.ndarray:
    """Module-level (picklable) wrapper: raw records in -> ordered feature
    matrix out (n_samples, 44) in the exact original notebook order."""
    return engineer_features(raw_df)[get_feature_columns()].values