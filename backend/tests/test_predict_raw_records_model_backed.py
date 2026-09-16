"""Criterion: raw-record inference path (Task 2B).

POST /api/predict with ``raw_records`` must derive the 44 features server-side
through the recovered original feature-engineering pipeline — the frontend is
never trusted to submit an engineered vector. These tests hit the live backend,
consistent with the rest of the backend test suite.
"""

import httpx


def _demo_anita(client: httpx.Client) -> dict:
    seed = client.post("/demo/seed")
    assert seed.status_code == 200, seed.text
    personnel = client.get("/demo/personnel")
    assert personnel.status_code == 200
    return next(p for p in personnel.json() if "Anita" in p["name"])


def test_predict_from_raw_records_is_model_backed(client: httpx.Client):
    anita = _demo_anita(client)
    assert len(anita["raw_records"]) == 4

    resp = client.post(
        "/predict",
        json={"personnel_id": anita["id"], "raw_records": anita["raw_records"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["predicted_band"] == "High"
    assert abs(body["risk_probability"] - 0.796) < 0.05
    total = sum(c["probability"] for c in body["class_probabilities"])
    assert abs(total - 1.0) < 1e-6

    # The stored assessment must carry the server-engineered 44 features
    # (derived from the raw records), not a client-supplied vector.
    assessments = client.get("/assessments")
    stored = next(a for a in assessments.json() if a["id"] == body["assessment_id"])
    assert len(stored["features"]) == 44
    for name in ("weekly_duty_hours", "weekly_duty_hours__roll4_mean", "weekly_duty_hours__delta_wow", "weekly_duty_hours__was_missing"):
        assert name in stored["features"]


def test_predict_rejects_engineered_vector_in_raw_records(client: httpx.Client):
    anita = _demo_anita(client)
    poisoned = [anita["raw_records"][0] | {"weekly_duty_hours__roll4_mean": 40.0}]
    resp = client.post(
        "/predict",
        json={"personnel_id": anita["id"], "raw_records": poisoned},
    )
    assert resp.status_code == 422
    assert "unexpected columns" in resp.json()["detail"]


def test_predict_rejects_client_supplied_engineered_features(client: httpx.Client):
    anita = _demo_anita(client)
    # The legacy pre-engineered vector was removed from the API surface: any
    # request carrying `features` must be rejected at the schema boundary.
    resp = client.post(
        "/predict",
        json={"personnel_id": anita["id"], "features": anita["features"]},
    )
    assert resp.status_code == 422
    assert "features" in resp.text


def test_predict_rejects_features_even_when_raw_records_are_present(client: httpx.Client):
    anita = _demo_anita(client)
    resp = client.post(
        "/predict",
        json={
            "personnel_id": anita["id"],
            "features": anita["features"],
            "raw_records": anita["raw_records"],
        },
    )
    assert resp.status_code == 422
    assert "features" in resp.text


def test_predict_requires_raw_records(client: httpx.Client):
    anita = _demo_anita(client)
    resp = client.post("/predict", json={"personnel_id": anita["id"]})
    assert resp.status_code == 422
    assert "raw_records" in resp.text


def test_predict_from_raw_records_rejects_missing_columns(client: httpx.Client):
    anita = _demo_anita(client)
    broken = [{"personnel_id": "demo-ms-042", "week": 0}]  # no static/raw columns
    resp = client.post(
        "/predict",
        json={"personnel_id": anita["id"], "raw_records": broken},
    )
    assert resp.status_code == 422
    assert "missing required columns" in resp.json()["detail"]


def test_predict_from_mixed_personnel_without_personnel_id_is_rejected(client: httpx.Client):
    anita = _demo_anita(client)
    client.get("/demo/personnel")
    second = next(p for p in client.get("/demo/personnel").json() if "Vikram" in p["name"])
    mixed = anita["raw_records"] + second["raw_records"]
    resp = client.post("/predict", json={"raw_records": mixed})
    assert resp.status_code == 422
    assert "single personnel_id" in resp.json()["detail"]