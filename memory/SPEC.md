# Manobal-AI living specification

## Purpose
Manobal-AI is a human-in-the-loop decision-support workspace for voluntary welfare check-ins and human follow-up for uniformed forces. It is not a diagnosis, disciplinary tool, self-harm predictor, or automated action system.

## AI contract
- `risk_model.pkl` is the serialized calibrated LightGBM multiclass classifier.
- `preprocessing_pipeline.pkl` is a 273-byte `FunctionTransformer` referencing `__main__.preprocess_for_inference`; its function source is not embedded. The backend uses a documented runtime compatibility adapter that preserves the metadata feature order and converts the 44 numeric inputs to a matrix. This limitation is exposed by `/api/model-info`.
- `model_metadata.json` is the source of truth for the 44 ordered feature names, model version `0.2.0-sih-final`, feature version `1.1.0`, and bands `Low`, `Moderate`, `High`.
- `/api/predict` returns real calibrated class probabilities and LightGBM contribution values. Confidence is the maximum calibrated class probability.
- `/api/predict` also returns a deterministic 0–100 Data Trust heuristic from missingness/completeness, live recency, documented source reliability and current-vs-rolling consistency. It is explicitly not model confidence.
- Risk + Trust Fusion returns `REVIEW_RECOMMENDED`, `MONITOR`, or `VERIFY_DATA`. Trust below 60 causes explicit abstention and never silently converts uncertainty into Low risk.
- Trajectory, early warning, What Changed, and welfare recommendations are clearly labeled derived platform logic based on stored history and human-safety policy, not model outputs.

## Data model
MongoDB collections: `personnel`, `wellness_logs`, `workload_records`, `deployment_history`, `leave_requests`, `risk_assessments`, and `interventions`.

## Key flows
1. Officer enters a personnel reference and all 44 model features in the responsive dashboard.
2. Frontend sends `{ personnel_id, features }` to `POST /api/predict`.
3. Backend validates exact keys and finite numeric values, runs the uploaded preprocessing artifact through its runtime hook, invokes the uploaded LightGBM artifact, stores the assessment, and returns the structured result.
4. The result panel shows band, probabilities, confidence basis, top model contributions, and human-led next steps.
5. The public landing page introduces Welfare Signal with the message “They protect us every day. Who protects their well-being?” and routes into a local demo role switch.
6. Demo entry seeds three clearly labeled synthetic personnel records and historical snapshots. Historical risk bands are produced by the real uploaded model, never hardcoded.
7. The welfare officer command view answers who needs attention, opens a personnel profile, calls the real `/api/predict`, explains the signal, compares stored history, and routes to the intervention desk.
8. Welfare officers can record a human assessment, intervention type, notes, follow-up date, and workflow status in MongoDB.
9. Personnel and Welfare Officer roles expose role-appropriate welfare and organizational views; AI analysis and privacy screens explain the model path and safeguards.

## Auth and roles
Demo authentication is a clearly labeled local role switch stored in browser session state; it is not real authentication and has no credentials. Roles are Personnel and Welfare Officer. Production deployment must add approved authentication, authorization, audit logging, and access controls before operational use.

## Demo data
- All named personnel and organizational values are synthetic and visibly labeled `DEMO DATA`.
- `POST /api/demo/seed` creates synthetic personnel and model-backed history records.
- `GET /api/demo/personnel` returns the feature snapshots used by the frontend.
- Demo predictions displayed after “Run AI analysis” always come from `POST /api/predict` using `risk_model.pkl`.