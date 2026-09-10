"""Criterion: Personnel risk profile runs the real backend model and explains the result.

POST /api/predict on demo-seeded features should return a Low/Moderate/High band,
risk probability, all class probabilities, and top LightGBM contributing factors.
"""

import httpx


def test_predict_returns_model_backed_explanation(client: httpx.Client):
    # Ensure demo data exists (idempotent reseed is fine for this read-only check).
    seed_resp = client.post("/demo/seed")
    assert seed_resp.status_code == 200, seed_resp.text

    personnel = client.get("/demo/personnel")
    assert personnel.status_code == 200
    people = personnel.json()
    anita = next(p for p in people if "Anita" in p["name"])

    resp = client.post(
        "/predict",
        json={"personnel_id": anita["id"], "features": anita["features"]},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["predicted_band"] in ("Low", "Moderate", "High")
    assert body["predicted_band"] == "High"
    assert 0.0 <= body["risk_probability"] <= 1.0
    assert abs(body["risk_probability"] - 0.796) < 0.05

    bands = {c["band"] for c in body["class_probabilities"]}
    assert bands == {"Low", "Moderate", "High"}

    assert len(body["top_contributing_factors"]) > 0
    for factor in body["top_contributing_factors"]:
        assert "feature" in factor and "contribution" in factor and "direction" in factor

    # trajectory / history-derived fields present and honestly labeled
    assert body["trajectory_status"] == "derived_from_history"
    assert len(body["trajectory"]) >= 1
    assert "early_warning" in body
    assert 0 <= body["data_trust"]["score"] <= 100
    assert body["data_trust"]["basis"].lower().find("not model confidence") >= 0
    assert body["decision_support"]["state"] in ("REVIEW_RECOMMENDED", "MONITOR", "VERIFY_DATA")


def test_model_info_discloses_version_and_adapter(client: httpx.Client):
    resp = client.get("/model-info")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model_version"] == "0.2.0-sih-final"
    assert body["preprocessing_status"] == "runtime_compatibility_adapter"
