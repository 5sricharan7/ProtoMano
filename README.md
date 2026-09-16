# Manobal-AI (Welfare Signal)

SIH 2026 prototype: a human-in-the-loop **decision-support** workspace for voluntary welfare check-ins and officer follow-up. The model outputs a Low / Moderate / High welfare-risk **signal**. It is not a diagnosis, disciplinary tool, self-harm predictor, or automated action system.

This repository is a **demo / prototype**, not a production deployment. There is no real authentication or RBAC. Demo entry is a local role switch (Personnel or Welfare Officer) stored in the browser.

## Architecture

- **Frontend:** Vite + React (TypeScript). Dev server on port `3000`. Calls the API with relative `/api/...` paths; Vite proxies `/api` to the backend.
- **Backend:** FastAPI (`backend/server.py`). Serves all app routes under `/api`.
- **Database:** MongoDB (Motor). Stores personnel, risk assessments, interventions, and optional welfare record collections.
- **Inference:** The backend loads serialized artifacts from `artifacts/` and runs `POST /api/predict`. The UI does not run the model in the browser.

The uploaded LightGBM classifier expects **44 numeric features** in the order documented by `artifacts/model_metadata.json` (model version `0.2.0-sih-final`, feature version `1.1.0`). A small preprocessing pickle is loaded at runtime; the backend uses a compatibility adapter that preserves that feature order and passes a numeric matrix to the model.

## Model artifacts

Keep these files in `artifacts/` (required for `/api/predict`, `/api/model-info`, and demo seeding):

- `risk_model.pkl` — calibrated LightGBM multiclass classifier
- `preprocessing_pipeline.pkl` — preprocessing transformer (runtime adapter)
- `baseline_model.pkl` — loaded with the other artifacts
- `model_metadata.json` — ordered 44 feature names, band order, versions
- `MODEL_CARD.md` — intended use and limitations (synthetic training data)

Override the artifact directory with `MODEL_ARTIFACT_DIR` if needed. The default is the repo `artifacts/` folder.

## Synthetic demo data

All named personnel and organizational values are **synthetic** and labeled DEMO DATA in the UI.

`POST /api/demo/seed` creates three demo records and historical assessments by running the **real** uploaded model (bands are not hardcoded). `GET /api/demo/personnel` returns those profiles and stored history for the frontend.

## Main user flow

1. Landing page (`/`) introduces Welfare Signal and links into the demo.
2. Demo entry (`/login`) chooses **Personnel** or **Welfare Officer**, then seeds demo data (no credentials).
3. Welfare officer command (`/officer`) shows who needs attention from the latest stored assessments.
4. Personnel profile (`/personnel/:id`) runs **Run AI analysis** → `POST /api/predict` with the personnel's raw weekly records (`raw_records`). The server derives the 44 features via the canonical feature-engineering pipeline; pre-engineered client-supplied vectors are rejected.
5. The result includes calibrated class probabilities, LightGBM feature contributions (when available), a data-trust heuristic, risk+trust fusion (`REVIEW_RECOMMENDED` / `MONITOR` / `VERIFY_DATA`), history-derived trajectory and “What Changed”, and rule-based welfare recommendations.
6. Intervention desk (`/interventions`) records a human review in MongoDB.
7. Supporting screens: personnel self-view (`/personnel`), static pipeline explainer (`/analysis`), cohort insights (`/insights`), privacy copy (`/ethics`).

Trajectory, early warning, What Changed, data trust, fusion, and recommendations are **platform logic** (or heuristics) on top of stored history and the model band — not extra trained models.

## Repository structure

```
artifacts/          Model pickle files, metadata, model card
backend/           FastAPI app, inference, Mongo access, pytest tests
  server.py         Application entry point
  routers/          Welfare API routes
  lib/              DB client and InferenceEngine
  tests/            Backend API tests (live server)
frontend/           Vite + React UI
tests/              Playwright workspace (scaffold; app tests live under backend/tests)
memory/SPEC.md      Living product notes
```

## Prerequisites

- Python 3 with packages from `backend/requirements.txt` (includes FastAPI, Motor, LightGBM, scikit-learn, joblib, pytest)
- Node.js + Yarn (frontend uses `frontend/yarn.lock`)
- A running **MongoDB** instance reachable from the backend

## Environment variables

Create `backend/.env` locally (this file is gitignored). Do not commit secrets.

| Variable | Required | Purpose |
|---|---|---|
| `MONGO_URL` | Yes | MongoDB connection string |
| `DB_NAME` | Yes | Database name |
| `CORS_ORIGINS` | No | Comma-separated allowed origins (default `*`) |
| `MODEL_ARTIFACT_DIR` | No | Directory containing the model artifacts |
| `APP_TZ` | No | Timezone for date helpers (default `UTC`) |
| `BACKEND_URL` | No | Base URL for pytest (`http://localhost:8001` by default) |

The frontend uses relative `/api` paths. `frontend/.env` is not required for the default local setup.

## Run the backend

From `backend/` (working directory must allow `server:app` and `lib/` imports):

```bash
pip install -r requirements.txt
# ensure MongoDB is running and backend/.env is set
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

API: `http://localhost:8001` (routes under `/api`).

## Run the frontend

From `frontend/`:

```bash
yarn install
yarn dev
```

UI: `http://localhost:3000`. The Vite config proxies `/api` to `http://localhost:8001`.

Run backend and frontend together. Login seeding and live analysis fail if the API or model artifacts are unavailable.

## Backend tests

Tests hit the **live** uvicorn process (not an in-process app). Start the backend first, then from `backend/`:

```bash
pytest
```

`pytest.ini` enables pytest-xdist (`-n 2`). For a serial run: `pytest -n 0`.

Coverage is the welfare predict/seed/intervention/reliability tests under `backend/tests/`. There is no in-repo Playwright e2e suite yet.

## Prototype limits (explicit)

- Demo role switch only — not production login, sessions, or access control.
- Trained on **synthetic** data; revalidation on authorized real data is required before any operational use.
- A human officer must review signals before welfare action. No automated messaging, diagnosis, or discipline.
