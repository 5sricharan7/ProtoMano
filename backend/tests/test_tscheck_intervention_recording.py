"""Criterion: Welfare officer can record human intervention.

POST /api/interventions persists a workflow status + human assessment record,
and it must then reappear via GET /api/interventions.
"""

import time

import httpx


def test_create_intervention_persists_and_lists(client: httpx.Client):
    # Fixture personnel: use demo-seeded Anita Rawat id (read-only reference, not mutated).
    personnel = client.get("/demo/personnel")
    assert personnel.status_code == 200
    people = personnel.json()
    assert len(people) > 0
    target = people[0]

    unique = f"tscheck-intervention-{int(time.time() * 1000)}"
    payload = {
        "personnel_id": target["id"],
        "intervention_type": "Voluntary welfare check-in",
        "notes": f"{unique}: officer recorded assessment and follow-up plan.",
        "owner": "Welfare officer · DEMO",
        "status": "UNDER REVIEW",
        "human_assessment": f"{unique}: human review completed, low concern after discussion.",
        "follow_up_date": "2026-12-01",
    }

    create_resp = client.post("/interventions", json=payload)
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert created["id"]
    assert created["status"] == "UNDER REVIEW"
    assert unique in created["notes"]

    list_resp = client.get("/interventions")
    assert list_resp.status_code == 200
    all_items = list_resp.json()
    match = next((i for i in all_items if i["id"] == created["id"]), None)
    assert match is not None, "created intervention did not appear in recent welfare actions list"
    assert match["human_assessment"] == payload["human_assessment"]
    assert match["personnel_id"] == target["id"]


def test_create_intervention_rejects_missing_required_fields(client: httpx.Client):
    resp = client.post("/interventions", json={"personnel_id": "tscheck-missing"})
    assert resp.status_code == 422
