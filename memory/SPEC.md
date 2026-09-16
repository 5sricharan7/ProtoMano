# Manobal-AI living specification

## Purpose
Manobal-AI is a human-in-the-loop decision-support workspace for voluntary welfare check-ins and human follow-up for uniformed forces. It is not a diagnosis, disciplinary tool, self-harm predictor, or automated action system.

## AI contract
- `risk_model.pkl` is the serialized calibrated LightGBM multiclass classifier.
- `preprocessing_pipeline.pkl` is a 273-byte `FunctionTransformer` referencing `lib.preprocessing.preprocess_for_inference`; its function source is not embedded. The backend uses a documented runtime compatibility adapter that preserves the metadata feature order and converts the 44 numeric inputs to a matrix. This limitation is exposed by `/api/model-info`.
- `model_metadata.json` is the source of truth for the 44 ordered feature names, model version `0.2.0-sih-final`, feature version `1.1.0`, and bands `Low`, `Moderate`, `High`.
- `lib/feature_engineering.py` is the canonical raw-record → 44-feature pipeline, vendored from the recovered original notebook (`AI_Personnel_Welfare_Risk_SIH_FINAL(3).ipynb`): sort by `[personnel_id, week]`; missingness indicators before imputation; causal per-person expanding-mean (incl. current week) → global median → 0.0 fallback; rolling-4 mean; week-over-week delta; static-first ordering. It is intentionally NOT re-derived.
- `POST /api/predict` derives the 44 features server-side from `raw_records` (raw weekly records) via `lib/feature_engineering`. This is the ONLY accepted input: `PredictRequest` forbids unknown fields, so a client-supplied engineered 44-feature vector (`features`) is rejected at the schema boundary (HTTP 422). The frontend is never trusted to submit an engineered vector.
- `/api/predict` returns real calibrated class probabilities and LightGBM contribution values. Confidence is the maximum calibrated class probability.
- `/api/predict` also returns a deterministic 0–100 Data Trust heuristic from missingness/completeness, live recency, documented source reliability and current-vs-rolling consistency. It is explicitly not model confidence.
- Risk + Trust Fusion returns `REVIEW_RECOMMENDED`, `MONITOR`, or `VERIFY_DATA`. Trust below 60 causes explicit abstention and never silently converts uncertainty into Low risk.
- Trajectory, early warning, What Changed, and welfare recommendations are clearly labeled derived platform logic based on stored history and human-safety policy, not model outputs.

## Data model
MongoDB collections: `personnel`, `wellness_logs`, `workload_records`, `deployment_history`, `leave_requests`, `risk_assessments`, and `interventions`.

## Key flows
1. Officer opens a personnel record; the frontend submits the demo person's raw weekly records (`raw_records`) to `POST /api/predict`.
2. Backend validates raw columns, rejects pre-engineered/unknown keys, runs the canonical `lib/feature_engineering` pipeline server-side to derive the exact 44 ordered features, runs the uploaded LightGBM artifact, stores the assessment, and returns the structured result.
3. The result panel shows band, probabilities, confidence basis, top model contributions, and human-led next steps.
4. The public landing page introduces Welfare Signal with the message "They protect us every day. Who protects their well-being?" and routes into a local demo role switch.
5. Demo entry seeds three clearly labeled synthetic personnel records and historical snapshots. Historical risk bands are produced by the real uploaded model, never hardcoded.
6. The welfare officer command view answers who needs attention, opens a personnel profile, calls the real `/api/predict`, explains the signal, compares stored history, and routes to the intervention desk.
7. Welfare officers can record a human assessment, intervention type, notes, follow-up date, and workflow status in MongoDB.
8. Personnel and Welfare Officer roles expose role-appropriate welfare and organizational views; AI analysis and privacy screens explain the model path and safeguards.

## Auth and roles
Demo authentication is a clearly labeled local role switch stored in browser session state; it is not real authentication and has no credentials. Roles are Personnel and Welfare Officer. Production deployment must add approved authentication, authorization, audit logging, and access controls before operational use.

## Demo data
- All named personnel and organizational values are synthetic and visibly labeled `DEMO DATA`.
- `POST /api/demo/seed` creates synthetic personnel and model-backed history records.
- `GET /api/demo/personnel` returns the feature snapshots used by the frontend.
- Demo predictions displayed after “Run AI analysis” always come from `POST /api/predict` using `risk_model.pkl`.