"""Task 2B — recovered original feature-engineering pipeline tests.

These are self-contained unit tests (no live backend / MongoDB required). They
pin the exact behavior recovered from ``AI_Personnel_Welfare_Risk_SIH_FINAL(3)``:
44 features, exact ordering, missingness-before-imputation, causal expanding-mean
imputation, global-median fallback, 0.0 fallback, rolling-4, week-over-week
delta, no future leakage, raw record -> 44 features -> model prediction, and a
clean-process import/inference check.
"""

import json
import subprocess
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lib.feature_engineering import (
    FEATURE_COUNT,
    RAW_NUMERIC_FEATURES,
    STATIC_FEATURES,
    engineer_features,
    features_for_latest_week,
    get_feature_columns,
    preprocess_for_inference,
    records_to_frame,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = BACKEND_DIR.parent / "artifacts"

DEFAULT_STATIC = {
    "years_of_service": 10.0,
    "hardship_posting_flag": False,
    "transfer_count_24mo": 2.0,
    "years_in_current_posting": 3.0,
}

DEFAULT_RAW = {
    "weekly_duty_hours": 48.0,
    "night_shift_ratio": 0.2,
    "overtime_hours": 5.0,
    "days_since_last_rest": 4.0,
    "days_since_last_leave": 30.0,
    "leave_balance": 20.0,
    "wellness_score_self_report": 8.0,
    "sleep_quality_score_self_report": 7.5,
    "resting_hr_trend_biometric": 0.1,
    "sleep_hours_biometric": 7.0,
}


def raw_record(person: str, week: int, overrides: dict | None = None) -> dict:
    record = {"personnel_id": person, "week": week, **DEFAULT_STATIC, **DEFAULT_RAW}
    if overrides:
        record.update(overrides)
    return record


def raw_frame(records: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(records)


@pytest.fixture
def artifact_metadata() -> dict:
    return json.loads((ARTIFACT_DIR / "model_metadata.json").read_text(encoding="utf-8"))


def test_exactly_44_features():
    assert FEATURE_COUNT == 44
    assert len(get_feature_columns()) == 44
    frame = raw_frame(
        [
            raw_record("P1", 0),
            raw_record("P1", 1),
            raw_record("P2", 0),
        ]
    )
    latest = features_for_latest_week(frame)
    assert latest.shape[1] == 1 + 44  # personnel_id + exactly 44 features
    matrix = preprocess_for_inference(frame)
    assert matrix.shape == (3, 44)


def test_exact_feature_ordering_matches_metadata(artifact_metadata):
    expected = [
        "years_of_service",
        "hardship_posting_flag",
        "transfer_count_24mo",
        "years_in_current_posting",
    ]
    for f in RAW_NUMERIC_FEATURES:
        expected.extend([f, f"{f}__roll4_mean", f"{f}__delta_wow", f"{f}__was_missing"])
    assert get_feature_columns() == expected
    assert get_feature_columns() == artifact_metadata["feature_list_in_order"]

    frame = raw_frame([raw_record("P1", 0), raw_record("P1", 1)])
    latest = features_for_latest_week(frame)
    assert latest.columns.tolist() == ["personnel_id"] + get_feature_columns()
    # static features first, then raw, roll4, delta, was_missing per feature
    assert latest.columns.tolist()[5:9] == [
        "weekly_duty_hours",
        "weekly_duty_hours__roll4_mean",
        "weekly_duty_hours__delta_wow",
        "weekly_duty_hours__was_missing",
    ]


def test_missingness_indicators_created_before_imputation():
    # Mid-series NaNs are imputed, but the __was_missing flags must still be 1
    # there (they record ORIGINAL missingness, before any fill).
    frame = raw_frame(
        [
            raw_record("P1", 0, {"weekly_duty_hours": 40.0}),
            raw_record("P1", 1, {"weekly_duty_hours": None}),
            raw_record("P1", 2, {"weekly_duty_hours": 42.0}),
            raw_record("P1", 3, {"weekly_duty_hours": None}),
        ]
    )
    eng = engineer_features(frame)
    sub = eng[["week", "weekly_duty_hours", "weekly_duty_hours__was_missing"]].copy()
    assert sub.loc[sub["week"] == 1, "weekly_duty_hours__was_missing"].iloc[0] == 1
    assert sub.loc[sub["week"] == 3, "weekly_duty_hours__was_missing"].iloc[0] == 1
    assert sub.loc[sub["week"] == 0, "weekly_duty_hours__was_missing"].iloc[0] == 0
    assert sub.loc[sub["week"] == 2, "weekly_duty_hours__was_missing"].iloc[0] == 0
    # imputed values reflect causal expanding means (40 for week1, 41 for week3)
    assert sub.loc[sub["week"] == 1, "weekly_duty_hours"].iloc[0] == 40.0
    assert sub.loc[sub["week"] == 3, "weekly_duty_hours"].iloc[0] == 41.0


def test_causal_expanding_mean_imputation():
    frame = raw_frame(
        [
            raw_record("P1", 0, {"weekly_duty_hours": None}),
            raw_record("P1", 1, {"weekly_duty_hours": 5.0}),
            raw_record("P1", 2, {"weekly_duty_hours": None}),
            raw_record("P1", 3, {"weekly_duty_hours": 6.0}),
        ]
    )
    eng = engineer_features(frame)
    sub = eng[["week", "weekly_duty_hours"]].copy()
    values = dict(zip(sub["week"], sub["weekly_duty_hours"]))
    assert values[2] == 5.0  # causal: only week<=2 observed (5.0), NOT mean(5,6)
    assert values[3] == 6.0  # observed value is preserved
    assert values[1] == 5.0
    assert values[0] == 5.0  # no prior observation -> global median of [5,5,6]


def test_global_median_fallback():
    frame = raw_frame(
        [
            raw_record("P1", 0, {"weekly_duty_hours": None}),
            raw_record("P1", 1, {"weekly_duty_hours": 40.0}),
            raw_record("P1", 2, {"weekly_duty_hours": 40.0}),
            raw_record("P1", 3, {"weekly_duty_hours": 40.0}),
            raw_record("P2", 0, {"weekly_duty_hours": 50.0}),
            raw_record("P2", 1, {"weekly_duty_hours": 50.0}),
            raw_record("P2", 2, {"weekly_duty_hours": 50.0}),
            raw_record("P2", 3, {"weekly_duty_hours": 50.0}),
        ]
    )
    eng = engineer_features(frame)
    p1_first = eng.loc[(eng["personnel_id"] == "P1") & (eng["week"] == 0), "weekly_duty_hours"].iloc[0]
    # global median of the partially-imputed column [40,40,40,50,50,50,50] -> 50.0
    assert p1_first == pytest.approx(50.0)


def test_zero_fallback_when_everything_missing():
    frame = raw_frame(
        [
            raw_record("P1", 0, {"sleep_hours_biometric": None}),
            raw_record("P1", 1, {"sleep_hours_biometric": None}),
            raw_record("P2", 0, {"sleep_hours_biometric": None}),
            raw_record("P2", 1, {"sleep_hours_biometric": None}),
        ]
    )
    eng = engineer_features(frame)
    assert (eng["sleep_hours_biometric"] == 0.0).all()
    assert (eng["sleep_hours_biometric__was_missing"] == 1).all()
    assert (eng["sleep_hours_biometric__roll4_mean"] == 0.0).all()
    assert (eng["sleep_hours_biometric__delta_wow"] == 0.0).all()


def test_rolling_4_week_mean():
    frame = raw_frame(
        [raw_record("P1", w, {"weekly_duty_hours": 40.0 + 4.0 * w}) for w in range(6)]
    )
    eng = engineer_features(frame)
    sub = eng[eng["personnel_id"] == "P1"].sort_values("week")
    expected = [40.0, 42.0, 44.0, 46.0, 50.0, 54.0]
    np.testing.assert_allclose(sub["weekly_duty_hours__roll4_mean"].values, expected)
    # min_periods=1: first week's rolling mean is the week itself
    assert sub["weekly_duty_hours__roll4_mean"].iloc[0] == 40.0


def test_week_over_week_delta():
    frame = raw_frame(
        [raw_record("P1", w, {"weekly_duty_hours": 40.0 + 4.0 * w}) for w in range(6)]
    )
    eng = engineer_features(frame)
    sub = eng[eng["personnel_id"] == "P1"].sort_values("week")
    np.testing.assert_allclose(sub["weekly_duty_hours__delta_wow"].values, [0.0, 4.0, 4.0, 4.0, 4.0, 4.0])


def test_no_future_records_influence_past_features():
    def build(weeks):
        return raw_frame([raw_record("P1", w, {"weekly_duty_hours": 40.0 + 4.0 * w}) for w in weeks])

    full = engineer_features(build([0, 1, 2, 3, 4, 5]))
    short = engineer_features(build([0, 1, 2, 3]))
    cols = get_feature_columns()
    # adding future weeks (4, 5) must leave weeks 0..3 byte-identical
    full_past = full.loc[full["week"] <= 3, cols].reset_index(drop=True)
    short_all = short[cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(full_past, short_all)

    # manual causal recomputation as a second guard (mirrors original leakage audit)
    eng = engineer_features(build([0, 1, 2, 3, 4, 5]))
    manual_roll = eng["weekly_duty_hours"].rolling(window=4, min_periods=1).mean()
    np.testing.assert_allclose(eng["weekly_duty_hours__roll4_mean"].values, manual_roll.values, atol=1e-6)
    manual_diff = eng["weekly_duty_hours"].diff(1).fillna(0.0)
    np.testing.assert_allclose(eng["weekly_duty_hours__delta_wow"].values, manual_diff.values, atol=1e-6)


def test_records_to_frame_controls_the_entry_point():
    # engineered keys must be rejected (frontend never trusted with a 44-vector)
    with pytest.raises(ValueError, match="unexpected columns"):
        records_to_frame(
            [raw_record("P1", 0, {"weekly_duty_hours__roll4_mean": 40.0})]
        )
    # missing required columns must be rejected
    with pytest.raises(ValueError, match="missing required columns"):
        records_to_frame([{"personnel_id": "P1", "week": 0}])
    # missing static fields must be rejected
    with pytest.raises(ValueError, match="static column"):
        records_to_frame(
            [dict(raw_record("P1", 0), years_of_service=None)]
        )
    # non-numeric week must be rejected
    with pytest.raises(ValueError, match="week"):
        records_to_frame(
            [dict(raw_record("P1", 0), week="not-a-week")]
        )
    # null raw numerics are allowed (causal imputation is the point)
    ok = records_to_frame([raw_record("P1", 0, {"weekly_duty_hours": None})])
    assert ok["weekly_duty_hours"].isna().iloc[0]


def test_raw_record_to_44_features_to_existing_model_prediction():
    from lib.inference import InferenceEngine

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        engine = InferenceEngine(ARTIFACT_DIR)
        engine.load()
        assert engine.feature_names == get_feature_columns()

        # A high-risk-ish ladder (severity 8 profile reproduced via raw records).
        records = [
            raw_record(
                "P1",
                w,
                {
                    "weekly_duty_hours": [64.0, 64.0, 54.0, 66.0][w],
                    "night_shift_ratio": [0.48, 0.48, 0.40, 0.56][w],
                    "overtime_hours": [12.0, 12.0, 9.4, 14.4][w],
                    "days_since_last_rest": [6.3, 6.3, 5.0, 9.8][w],
                    "days_since_last_leave": [76.0, 76.0, 62.0, 154.0][w],
                    "leave_balance": [14.0, 14.0, 12.0, 8.0][w],
                    "wellness_score_self_report": [4.1, 4.1, 5.5, 3.5][w],
                    "sleep_quality_score_self_report": [4.4, 4.4, 5.9, 3.9][w],
                    "resting_hr_trend_biometric": [2.3, 2.3, 2.6, 2.6][w],
                    "sleep_hours_biometric": [5.8, 5.8, 6.7, 5.5][w],
                    "years_of_service": 12.0,
                    "hardship_posting_flag": True,
                    "transfer_count_24mo": 4.0,
                    "years_in_current_posting": 2.2,
                },
            )
            for w in range(4)
        ]
        result, features = engine.predict_from_raw_records(records, personnel_id="P1")

    assert result["predicted_band"] in ("Low", "Moderate", "High")
    assert set(features) == set(engine.feature_names) and len(features) == 44
    total = sum(item["probability"] for item in result["class_probabilities"])
    assert abs(total - 1.0) < 1e-6
    assert 0.0 <= result["prediction_confidence"] <= 1.0


def test_predict_from_raw_records_requires_single_person():
    from lib.inference import InferenceEngine

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        engine = InferenceEngine(ARTIFACT_DIR)
        engine.load()

        mixed = [raw_record("P1", 0), raw_record("P2", 0)]
        with pytest.raises(ValueError, match="single personnel_id"):
            engine.predict_from_raw_records(mixed)

        mismatch = [raw_record("P1", w, {"weekly_duty_hours": 30.0 + w}) for w in range(3)]
        with pytest.raises(ValueError, match="do not contain the supplied personnel_id"):
            engine.predict_from_raw_records(mismatch, personnel_id="P2")


def test_clean_process_import_and_inference():
    """Run the full raw -> 44 -> model path in a fresh subprocess interpreter."""
    test_script = (
        "import sys, json, warnings\n"
        f"sys.path.insert(0, {str(BACKEND_DIR)!r})\n"
        "warnings.filterwarnings('ignore')\n"
        "import joblib\n"
        "import pandas as pd\n"
        "from lib.feature_engineering import get_feature_columns, engineer_features, records_to_frame\n"
        "from lib.preprocessing import preprocess_for_inference\n"
        f"ARTIFACTS = {str(ARTIFACT_DIR)!r}\n"
        "meta = json.load(open(ARTIFACTS + '/model_metadata.json', encoding='utf-8'))\n"
        "assert get_feature_columns() == meta['feature_list_in_order'], 'feature order mismatch'\n"
        "model = joblib.load(ARTIFACTS + '/risk_model.pkl')\n"
        "pipeline = joblib.load(ARTIFACTS + '/preprocessing_pipeline.pkl')\n"
        "assert model.n_features_in_ == 44 and len(get_feature_columns()) == 44\n"
        "rec = {'personnel_id': 'P1', 'week': 0, 'years_of_service': 10.0,"
        "'hardship_posting_flag': False, 'transfer_count_24mo': 2.0,"
        "'years_in_current_posting': 3.0, 'weekly_duty_hours': 48.0,"
        "'night_shift_ratio': 0.2, 'overtime_hours': 5.0, 'days_since_last_rest': 4.0,"
        "'days_since_last_leave': 30.0, 'leave_balance': 20.0,"
        "'wellness_score_self_report': 8.0, 'sleep_quality_score_self_report': 7.5,"
        "'resting_hr_trend_biometric': 0.1, 'sleep_hours_biometric': 7.0}\n"
        "raw = pd.DataFrame([rec])\n"
        "frame = engineer_features(raw)\n"
        "ordered = frame[get_feature_columns()]\n"
        "X = preprocess_for_inference(ordered)\n"
        "assert X.shape == (1, 44), X.shape\n"
        "proba = model.predict_proba(X)\n"
        "assert abs(float(proba.sum(1)[0]) - 1.0) < 1e-6\n"
        "print('CLEAN-PROCESS-OK', int(model.predict(X)[0]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", test_script],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"clean process failed:\n{result.stdout}\n{result.stderr}"
    assert "CLEAN-PROCESS-OK" in result.stdout