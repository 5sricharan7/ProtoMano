"""P0/P1 reliability regression tests for the real model-backed demo flow."""

from datetime import datetime, timedelta, timezone
import time

import httpx
import pytest
from fastapi import HTTPException

from routers import welfare


def _demo_person(client: httpx.Client) -> dict:
    seed = client.post("/demo/seed")
    assert seed.status_code == 200, seed.text
    response = client.get("/demo/personnel")
    assert response.status_code == 200, response.text
    return response.json()[0]


def test_missing_feature_returns_422(client: httpx.Client):
    response = client.post("/predict", json={"features": {}})
    assert response.status_code == 422
    assert len(response.json()["detail"]["missing_features"]) == 44


def test_valid_prediction_probabilities_trust_and_persistence(client: httpx.Client):
    person = _demo_person(client)
    unique_id = f"reliability-{int(time.time() * 1000)}"
    response = client.post("/predict", json={"personnel_id": unique_id, "features": person["features"]})
    assert response.status_code == 200, response.text
    body = response.json()
    probabilities = [item["probability"] for item in body["class_probabilities"]]
    assert len(probabilities) == 3
    assert all(0 <= probability <= 1 for probability in probabilities)
    assert abs(sum(probabilities) - 1.0) < 1e-6
    assert 0 <= body["data_trust"]["score"] <= 100
    assert body["decision_support"]["state"] in ("REVIEW_RECOMMENDED", "MONITOR")

    assessments = client.get("/assessments")
    assert assessments.status_code == 200, assessments.text
    assert any(item["id"] == body["assessment_id"] and item["personnel_id"] == unique_id for item in assessments.json())


def test_low_trust_abstains_and_never_becomes_low_risk_by_default(client: httpx.Client):
    person = _demo_person(client)
    low_trust_features = dict(person["features"])
    for feature in low_trust_features:
        if feature.endswith("__was_missing"):
            low_trust_features[feature] = 1.0
    response = client.post("/predict", json={"personnel_id": "low-trust-test", "features": low_trust_features})
    assert response.status_code == 200, response.text
    body = response.json()
    assert 0 <= body["data_trust"]["score"] < body["data_trust"]["threshold"] <= 100
    assert body["decision_support"]["state"] == "VERIFY_DATA"
    assert body["decision_support"]["abstained"] is True
    assert "verify" in body["decision_support"]["basis"].lower()


def test_trajectory_direction_uses_chronological_order():
    now = datetime.now(timezone.utc)
    rising_unsorted = [
        {"assessed_at": now, "risk_probability": 0.8},
        {"assessed_at": now - timedelta(days=14), "risk_probability": 0.2},
        {"assessed_at": now - timedelta(days=7), "risk_probability": 0.5},
    ]
    falling_unsorted = [
        {"assessed_at": now - timedelta(days=7), "risk_probability": 0.5},
        {"assessed_at": now, "risk_probability": 0.2},
        {"assessed_at": now - timedelta(days=14), "risk_probability": 0.8},
    ]
    assert welfare._trajectory_direction(rising_unsorted) == "rising"
    assert welfare._trajectory_direction(falling_unsorted) == "falling"
    assert "rising" in welfare._early_warning("Moderate", rising_unsorted).basis
    assert "falling" in welfare._early_warning("Moderate", falling_unsorted).basis


def test_artifact_failure_is_clear_503(monkeypatch: pytest.MonkeyPatch):
    original_error = welfare.engine.load_error
    monkeypatch.setattr(welfare.engine, "load_error", "risk_model.pkl is unavailable")
    with pytest.raises(HTTPException) as error:
        welfare._ensure_engine_ready()
    assert error.value.status_code == 503
    assert "risk_model.pkl" in str(error.value.detail)
    monkeypatch.setattr(welfare.engine, "load_error", original_error)


def test_seed_marks_exactly_one_latest_snapshot_per_demo_person(client: httpx.Client):
    person = _demo_person(client)
    assessments = client.get("/assessments")
    assert assessments.status_code == 200, assessments.text
    seeded = [item for item in assessments.json() if item.get("personnel_id") == person["id"] and "history" in item.get("id", "")]
    assert len(seeded) == 3
    assert sum(bool(item.get("is_latest")) for item in seeded) == 1
    newest = max(seeded, key=lambda item: item["assessed_at"])
    assert newest["is_latest"] is True