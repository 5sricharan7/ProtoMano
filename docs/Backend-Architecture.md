Manobal-AI --- Backend Architecture

AI-Assisted Welfare Signal & Human-in-the-Loop Decision Support Backend

Manobal-AI is a welfare-oriented decision-support platform designed for
uniformed personnel.
Its backend is responsible for secure data handling, canonical feature
engineering, AI inference, historical analysis, data-trust evaluation,
risk/trust fusion, welfare recommendations, and recording human-reviewed
interventions.

Core Principle: AI should assist. Humans should decide.

📌 Backend Overview

The Manobal-AI backend is built with FastAPI and acts as the central
application and inference layer between the React frontend, MongoDB, and
the serialized machine-learning artifacts.

The backend follows a clear separation of responsibilities:

API Layer --- exposes REST endpoints to the frontend.

Validation Layer --- validates incoming requests and rejects
unsupported/pre-engineered inputs.

Feature Engineering Layer --- converts raw weekly welfare
records into the canonical 44-feature vector.

ML Inference Layer --- loads the calibrated LightGBM model and
preprocessing artifacts and generates risk probabilities.

Decision-Support Layer --- combines model output with data trust
and historical context.

Historical Intelligence Layer --- analyzes previous assessments
and trajectory.

Recommendation Layer --- generates rule-based welfare-oriented
recommendations.

Persistence Layer --- stores personnel, assessments, and
intervention/review records in MongoDB.

Human Oversight Layer --- keeps the welfare officer in control
of any follow-up action.

🏗️ High-Level Backend Architecture

                         ┌──────────────────────────┐
                         │      React Frontend      │
                         │     Vite + TypeScript    │
                         └────────────┬─────────────┘
                                      │
                              REST / JSON APIs
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │        FastAPI Backend            │
                    │                                  │
                    │  API Routes / Request Validation │
                    └───────────────┬──────────────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
      ┌───────────────┐    ┌────────────────┐    ┌─────────────────┐
      │ Personnel &   │    │ Feature        │    │ Historical      │
      │ Welfare Data  │    │ Engineering    │    │ Intelligence    │
      └───────┬───────┘    └───────┬────────┘    └────────┬────────┘
              │                     │                      │
              │                     ▼                      │
              │            ┌────────────────┐             │
              │            │ 44-Feature     │             │
              │            │ Canonical Input │             │
              │            └───────┬────────┘             │
              │                    │                      │
              │                    ▼                      │
              │            ┌────────────────┐             │
              │            │ Preprocessing  │             │
              │            │ Pipeline       │             │
              │            └───────┬────────┘             │
              │                    │                      │
              │                    ▼                      │
              │            ┌────────────────┐             │
              │            │ Calibrated     │             │
              │            │ LightGBM Model │             │
              │            └───────┬────────┘             │
              │                    │                      │
              │                    ▼                      │
              │            ┌────────────────┐             │
              │            │ Risk Signal +  │◄────────────┘
              │            │ Probabilities  │
              │            └───────┬────────┘
              │                    │
              │                    ▼
              │            ┌────────────────┐
              └───────────►│ Data Trust +   │
                           │ Risk Fusion     │
                           └───────┬────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Welfare Officer    │
                         │ Human Review       │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Intervention /    │
                         │ Follow-up Record  │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │     MongoDB        │
                         └────────────────────┘

1. Backend Design Goals

The backend architecture is designed around the following goals:

🔹 1. Secure Data Processing

Personnel welfare data should remain within the controlled backend
boundary instead of being processed directly inside the browser.

🔹 2. Canonical ML Input

The frontend sends raw weekly records. The backend derives the model
input using the canonical feature-engineering pipeline.

This prevents clients from manually supplying arbitrary pre-engineered
model vectors.

🔹 3. Explainable Decision Support

The backend does not return only a prediction. It combines:

calibrated class probabilities

model feature contributions when available

data-trust information

historical trajectory

change detection

risk/trust fusion

welfare-oriented recommendations

🔹 4. Human-in-the-Loop Operation

The backend provides signals to a welfare officer rather than
autonomously taking welfare or disciplinary action.

🔹 5. Modular Architecture

API routing, inference, feature engineering, database operations, and
decision-support logic are kept as separate responsibilities so that the
system can evolve without rewriting the entire backend.

2. Backend Technology Stack

Layer                  Technology

Backend Framework      FastAPI
Language               Python
Database               MongoDB
MongoDB Driver         Motor
API Format             REST / JSON
ML Model               Calibrated LightGBM
Preprocessing          Serialized preprocessing pipeline
Validation / Schemas   Pydantic
Server                 Uvicorn
Testing                Pytest
Configuration          Environment variables / .env
Frontend Consumer      React + Vite + TypeScript

3. Backend Layer Architecture

The backend can be understood as six logical layers.

┌──────────────────────────────────────────────┐
│                 API Layer                    │
│ FastAPI routes, request/response handling    │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│            Validation Layer                   │
│ Pydantic schemas + input constraints         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│       Feature Engineering / Domain Layer     │
│ Raw welfare records → canonical features     │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              ML Inference Layer              │
│ Preprocessing → LightGBM → probabilities     │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│          Decision-Support Layer              │
│ Trust + history + fusion + recommendations   │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│             Persistence Layer                │
│ MongoDB personnel, assessments, reviews      │
└──────────────────────────────────────────────┘

4. API Layer

FastAPI provides the HTTP interface consumed by the React frontend.

The API layer is responsible for:

receiving requests

validating payloads

calling application services

returning structured JSON responses

handling errors

keeping model execution on the server

The frontend does not execute the LightGBM model.

5. Core Backend Request Flow

A typical AI analysis request follows this sequence:

Frontend
   │
   │ POST /api/predict
   │ raw_records
   ▼
FastAPI Route
   │
   ▼
Request Validation
   │
   ▼
Canonical Feature Engineering
   │
   ▼
44 Ordered Features
   │
   ▼
Preprocessing Pipeline
   │
   ▼
Calibrated LightGBM
   │
   ├── Class Probabilities
   └── Feature Contributions
   │
   ▼
Data Trust Evaluation
   │
   ▼
Historical Context
   │
   ▼
Risk + Trust Fusion
   │
   ▼
Welfare Recommendations
   │
   ▼
Structured JSON Response
   │
   ▼
Frontend Dashboard

6. Server-Side Feature Engineering

One of the most important backend design decisions is that feature
engineering is performed on the server.

The client submits raw weekly welfare records rather than a precomputed
ML vector.

Example

Raw Weekly Records
        │
        ▼
Backend Feature Engineering
        │
        ├── Aggregate signals
        ├── Temporal features
        ├── Workload indicators
        ├── Leave / activity indicators
        └── Other canonical transformations
        │
        ▼
44 Numeric Features
        │
        ▼
Model Preprocessing
        │
        ▼
LightGBM

Why this matters

This architecture:

keeps the feature definition centralized

reduces client-side manipulation

ensures training/inference consistency

makes model upgrades easier

prevents arbitrary pre-engineered vectors from being submitted by
the UI

The backend rejects unsupported pre-engineered client vectors and
expects the canonical raw-record format.

7. 44-Feature Inference Architecture

The current model expects 44 numeric features in a specific order.

The ordering is controlled through:

artifacts/model_metadata.json

The backend therefore treats the model metadata as part of the inference
contract.

Raw Records
    │
    ▼
Canonical Feature Engineering
    │
    ▼
Feature Names + Ordering
    │
    ▼
44 Numeric Feature Vector
    │
    ▼
Preprocessing Pipeline
    │
    ▼
Calibrated LightGBM Model

This prevents a valid-looking vector with incorrect feature ordering
from silently producing an invalid inference result.

8. ML Inference Layer

The ML layer loads serialized artifacts from the configured artifact
directory.

Current artifacts include:

artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md

Current model metadata

Model Version:   0.2.0-sih-final
Feature Version: 1.1.0
Input Features:  44 numeric features
Model:           Calibrated LightGBM

The artifact directory can be configured through:

MODEL_ARTIFACT_DIR

9. Inference Pipeline

The complete inference pipeline is:

1. Receive raw_records
          │
          ▼
2. Validate request
          │
          ▼
3. Build canonical features
          │
          ▼
4. Verify 44-feature contract
          │
          ▼
5. Apply preprocessing pipeline
          │
          ▼
6. Run calibrated LightGBM
          │
          ▼
7. Generate class probabilities
          │
          ▼
8. Calculate feature contributions
   when available
          │
          ▼
9. Evaluate data trust
          │
          ▼
10. Retrieve historical context
          │
          ▼
11. Perform risk + trust fusion
          │
          ▼
12. Generate welfare recommendations
          │
          ▼
13. Return structured response

10. Risk Signal Layer

The ML model generates a calibrated risk signal rather than directly
deciding what action should be taken.

The backend can expose:

predicted risk class

calibrated class probabilities

relevant feature contributions

contextual information required by the dashboard

The distinction is important:

AI Model
   │
   ▼
Risk Signal
   │
   ▼
Decision Support
   │
   ▼
Human Review
   │
   ▼
Welfare Follow-up

The model does not directly trigger disciplinary action, automated
messaging, or intervention.

11. Data Trust Layer

Risk output is interpreted together with a data-trust heuristic.

The purpose is to distinguish:

High-confidence signal
        from
Potentially unreliable data

Data trust can consider characteristics of the available input and its
quality.

The resulting system can surface a state such as:

REVIEW_RECOMMENDED
MONITOR
VERIFY_DATA

These states are decision-support outputs of the platform and are not
additional trained ML models.

12. Risk + Trust Fusion

The backend does not treat model probability as the entire decision
context.

Instead:

                ┌──────────────────┐
                │   ML Risk Signal │
                └────────┬─────────┘
                         │
                         ▼
                ┌──────────────────┐
                │   Risk + Trust   │
                │      Fusion      │
                └────────┬─────────┘
                         ▲
                         │
                ┌────────┴─────────┐
                │   Data Trust     │
                │    Heuristic     │
                └──────────────────┘
                         │
                         ▼
                 Decision Support

This makes the system more transparent because a welfare officer can
distinguish between:

a meaningful risk signal

a signal that should be monitored

a case where the underlying data should first be verified

13. Historical Intelligence Layer

The backend maintains historical assessment context in MongoDB.

Historical records allow the platform to analyze:

previous risk assessments

changes over time

trajectory

historical patterns

recent deviations

The current assessment is therefore interpreted in relation to previous
observations rather than being treated as an isolated prediction.

Previous Assessments
        │
        ▼
Historical Context
        │
        ├── Trajectory
        ├── Recent Change
        └── Historical Comparison
        │
        ▼
Current AI Assessment
        │
        ▼
Contextual Welfare Signal

14. "What Changed" Layer

The backend can derive a human-readable view of meaningful changes
between the current data and historical context.

Conceptually:

Historical Baseline
        │
        ▼
Current Weekly Data
        │
        ▼
Feature / Signal Comparison
        │
        ▼
Meaningful Changes
        │
        ▼
"What Changed"

This gives the welfare officer contextual information instead of
presenting only a risk label.

15. Welfare Recommendation Layer

Recommendations are generated through platform logic and rules.

They are not another trained predictive model.

The backend can combine:

Risk Signal
    +
Data Trust
    +
Historical Context
    +
Observed Changes
    ↓
Welfare Recommendations

The purpose is to help the officer decide what type of follow-up may be
appropriate.

The final action remains with the authorized human reviewer.

16. Human-in-the-Loop Architecture

Human oversight is a core backend boundary.

                 AI Analysis
                     │
                     ▼
              Welfare Signal
                     │
                     ▼
             Officer Dashboard
                     │
                     ▼
              Human Review
               /         \
              /           \
             ▼             ▼
       Monitor /        Follow-up /
       No Action        Intervention
                           │
                           ▼
                  Intervention Record
                           │
                           ▼
                       MongoDB

The backend records human review rather than allowing the model to
autonomously execute welfare actions.

17. Intervention Architecture

Interventions represent the human-reviewed response to an AI-assisted
signal.

A simplified flow is:

AI Assessment
      │
      ▼
Officer Review
      │
      ├── Review decision
      ├── Follow-up details
      └── Intervention information
      │
      ▼
Intervention API
      │
      ▼
MongoDB

This creates an auditable separation between:

Model Output ≠ Human Decision

18. MongoDB Persistence Architecture

MongoDB is used as the backend persistence layer.

The backend stores application information such as:

personnel profiles

welfare-related records

risk assessments

historical assessments

intervention / review records

synthetic demo records

A simplified logical structure is:

MongoDB
│
├── Personnel
│   └── Profile / context
│
├── Assessments
│   ├── Current result
│   ├── Probabilities
│   ├── Trust information
│   └── Historical assessment data
│
├── Interventions
│   ├── Human review
│   └── Follow-up information
│
└── Demo / Welfare Records
    └── Synthetic prototype data

19. Historical Assessment Persistence

Every assessment can contribute to a personnel-level historical context.

Personnel
   │
   ├── Assessment 1
   │
   ├── Assessment 2
   │
   ├── Assessment 3
   │
   └── Current Assessment
            │
            ▼
      Historical Analysis

This supports trajectory-based decision support without requiring the
frontend to reconstruct the history itself.

20. Demo Data Architecture

The prototype includes a controlled synthetic-data workflow.

POST /api/demo/seed
          │
          ▼
Generate Synthetic Demo Records
          │
          ▼
Run Real Uploaded Model
          │
          ▼
Create Historical Assessments
          │
          ▼
Store in MongoDB
          │
          ▼
Demo Dashboard

The demo workflow is designed to demonstrate the complete architecture
without requiring operational personnel data.

21. API Architecture

The backend exposes API routes under:

/api

Important functional areas include:

/api/predict
/api/demo/seed
/api/demo/personnel
/api/interventions

The exact route organization is maintained inside the backend router
structure.

Prediction

POST /api/predict

Purpose:

receive raw weekly records

perform server-side feature engineering

run the trained model

generate risk probabilities

evaluate data trust

incorporate historical context

return decision-support information

Demo Seed

POST /api/demo/seed

Purpose:

create synthetic demonstration personnel

generate historical assessment context

run the actual uploaded model

populate the prototype database

Demo Personnel

GET /api/demo/personnel

Purpose:

retrieve synthetic personnel profiles

retrieve historical assessment context for the demo interface

Interventions

/api/interventions

Purpose:

record human-reviewed welfare follow-up / intervention information

22. Backend Repository Architecture

The backend is organized as a modular Python application.

backend/
│
├── server.py
│
├── routers/
│   ├── ...
│   └── API route modules
│
├── lib/
│   ├── ...
│   └── Core backend / domain services
│
├── tests/
│   └── Backend test suite
│
└── requirements.txt

The repository also contains:

artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md

23. Configuration Architecture

The backend uses environment-based configuration.

Important variables include:

MONGO_URL=
DB_NAME=
CORS_ORIGINS=
MODEL_ARTIFACT_DIR=
APP_TZ=
BACKEND_URL=

Required

MONGO_URL
DB_NAME

Optional

CORS_ORIGINS
MODEL_ARTIFACT_DIR
APP_TZ
BACKEND_URL

Keeping configuration outside application code makes deployment and
environment changes easier.

24. CORS and Frontend Communication

The frontend communicates with backend endpoints using relative
/api/... paths.

The Vite development server proxies API traffic to the FastAPI backend.

Browser
   │
   │ /api/...
   ▼
Vite Development Server
   │
   │ Proxy
   ▼
FastAPI
   │
   ▼
Backend Services

CORS behavior can be configured through:

CORS_ORIGINS

25. Backend Security Boundary

The architecture intentionally keeps sensitive processing on the server.

┌────────────────────────────────────┐
│            Frontend                │
│                                    │
│ UI + request composition            │
└──────────────────┬─────────────────┘
                   │
             Controlled API
                   │
┌──────────────────▼─────────────────┐
│             Backend                │
│                                    │
│ Validation                         │
│ Feature Engineering                │
│ ML Inference                       │
│ Historical Analysis                │
│ Decision Support                   │
│ Persistence                        │
└────────────────────────────────────┘

The browser does not directly access:

the serialized ML model

preprocessing artifacts

database credentials

MongoDB

internal feature-engineering logic

26. Responsible AI Boundary

Manobal-AI is designed as a welfare decision-support system, not an
autonomous authority.

The backend therefore follows these boundaries:

Capability                           Backend Role

Stress/welfare signal                Generate AI-assisted signal
Diagnosis                            ❌ Not performed
Automatic discipline                 ❌ Not performed
Automatic welfare action             ❌ Not performed
Officer review                       ✅ Required
Historical context                   ✅ Supported
Data-trust evaluation                ✅ Supported
Human-reviewed intervention record   ✅ Supported
Synthetic demo data                  ✅ Supported

27. Model vs Platform Logic

A major architectural distinction is maintained between trained ML
components and platform decision-support logic.

Trained Components

Preprocessing Pipeline
        +
Calibrated LightGBM Model

Platform Logic

Feature Engineering
Data Trust Heuristic
Historical Trajectory
"What Changed"
Risk + Trust Fusion
Welfare Recommendations

This separation makes the architecture easier to explain, validate, and
improve.

28. End-to-End Backend Architecture

                    RAW WELFARE DATA
                           │
                           ▼
                 ┌──────────────────┐
                 │ FastAPI Endpoint │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Request          │
                 │ Validation       │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Canonical Feature│
                 │ Engineering      │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ 44 Feature       │
                 │ Contract         │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Preprocessing    │
                 │ Pipeline         │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Calibrated       │
                 │ LightGBM         │
                 └────────┬─────────┘
                          │
             ┌────────────┴─────────────┐
             │                          │
             ▼                          ▼
     Risk Probabilities          Feature Contributions
             │                          │
             └────────────┬─────────────┘
                          ▼
                 ┌──────────────────┐
                 │ Data Trust       │
                 │ Evaluation       │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Historical       │
                 │ Context          │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Risk + Trust     │
                 │ Fusion           │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Welfare          │
                 │ Recommendations  │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Welfare Officer  │
                 │ Human Review     │
                 └────────┬─────────┘
                          │
                          ▼
                 ┌──────────────────┐
                 │ Intervention /   │
                 │ Follow-up Record │
                 └────────┬─────────┘
                          │
                          ▼
                       MongoDB

29. Prototype vs Production Backend

The current implementation is a prototype intended for SIH
demonstration.

Area                    Current Prototype        Production Direction

Authentication          Demo role switch         Enterprise
authentication + RBAC

Database                MongoDB                  Hardened managed
deployment

Data                    Synthetic demo data      Authorized operational
data

ML model                Synthetic-data-trained   Revalidated with
artifact                 authorized real data

API                     FastAPI REST             Hardened API gateway /
service deployment

Secrets                 Environment              Managed secret
configuration            infrastructure

Auditability            Intervention records     Immutable audit logging

Monitoring              Development/test setup   Production
observability

Deployment              Local / prototype        Containerized
cloud/on-prem
deployment

These production items are architectural directions, not claims that
they are already implemented.

30. Testing Architecture

Backend tests are maintained under:

backend/tests/

The project uses:

pytest

Tests can be executed with:

pytest

For serial execution:

pytest -n 0

The test architecture is intended to validate:

API behavior

inference flow

request validation

feature engineering

backend logic

persistence behavior

integration behavior

31. Backend Startup

From the backend directory:

cd backend

Install dependencies:

pip install -r requirements.txt

Start FastAPI:

uvicorn server:app --host 0.0.0.0 --port 8001 --reload

The backend is then available for frontend API communication.

32. Backend Data Flow Summary

                 ┌──────────────────────┐
                 │   Raw User / Demo    │
                 │       Records        │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │       FastAPI        │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Validation + Feature │
                 │ Engineering          │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ 44-Feature Vector    │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ ML Preprocessing     │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Calibrated LightGBM  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Risk + Explainability│
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Trust + Historical   │
                 │ Decision Support     │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ Human Officer Review │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │ MongoDB Persistence  │
                 └──────────────────────┘

33. Why This Backend Architecture?

The backend architecture was designed around a simple principle:

The model produces a signal; the platform provides context; the
human makes the decision.

This architecture provides:

centralized AI inference

consistent feature engineering

controlled model access

historical context

data-quality awareness

explainable signals

auditable human review

modular backend services

a clear path toward production hardening

34. Future Backend Scalability

The architecture can be extended without changing the core welfare
decision-support principle.

Potential future directions include:

Current Prototype
      │
      ▼
Production Authentication
      │
      ▼
Role-Based Access Control
      │
      ▼
Secure Data Ingestion
      │
      ▼
Authorized Real-Data Validation
      │
      ▼
Model Registry / Versioning
      │
      ▼
Audit Logging
      │
      ▼
Monitoring + Observability
      │
      ▼
Scalable Deployment

The model and platform logic should continue to remain separated so that
future model versions can be validated and deployed without redesigning
the entire application.

35. Backend Architecture Principles

1. Server-Side Inference

ML inference remains inside the backend.

2. Canonical Feature Pipeline

Raw records are transformed into the official 44-feature representation
on the server.

3. Separation of Concerns

API, database, ML, feature engineering, and decision-support
responsibilities remain modular.

4. Human-in-the-Loop

AI output is presented for human review rather than autonomous action.

5. Context Over Isolated Prediction

Current signals are interpreted alongside historical information and
data trust.

6. Transparent AI

The system exposes probabilities, relevant contributions when available,
and supporting context.

7. Privacy-Oriented Design

Database and model artifacts remain behind the backend boundary.

8. Production-Aware Architecture

The prototype is structured so authentication, RBAC, auditing,
observability, and secure deployment can be added later.

36. Backend Architecture at a Glance

Component                 Responsibility

FastAPI                   Backend API and application server
Pydantic                  Request / response validation
Feature Engineering       Raw records → 44 canonical features
Preprocessing Pipeline    ML input transformation
LightGBM                  Welfare-risk classification
Data Trust                Input reliability heuristic
Historical Intelligence   Trajectory and historical context
Risk + Trust Fusion       Contextual decision-support state
Recommendations           Rule-based welfare guidance
MongoDB                   Persistent application data
Intervention API          Human-reviewed follow-up records
Pytest                    Backend testing
Uvicorn                   ASGI server

37. Architecture Summary

┌───────────────────────────────────────────────────────────────┐
│                       MANOBAL-AI BACKEND                      │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  React Frontend                                               │
│        │                                                      │
│        ▼                                                      │
│  FastAPI REST API                                             │
│        │                                                      │
│        ▼                                                      │
│  Request Validation                                           │
│        │                                                      │
│        ▼                                                      │
│  Canonical Feature Engineering                               │
│        │                                                      │
│        ▼                                                      │
│  44-Feature Contract                                          │
│        │                                                      │
│        ▼                                                      │
│  Preprocessing Pipeline                                       │
│        │                                                      │
│        ▼                                                      │
│  Calibrated LightGBM                                          │
│        │                                                      │
│        ├──────────────► Risk Probabilities                    │
│        │                                                      │
│        └──────────────► Feature Contributions                 │
│        │                                                      │
│        ▼                                                      │
│  Data Trust + Historical Intelligence                         │
│        │                                                      │
│        ▼                                                      │
│  Risk + Trust Fusion                                          │
│        │                                                      │
│        ▼                                                      │
│  Welfare Recommendations                                      │
│        │                                                      │
│        ▼                                                      │
│  Human Welfare Officer Review                                 │
│        │                                                      │
│        ▼                                                      │
│  Intervention / Follow-up                                     │
│        │                                                      │
│        ▼                                                      │
│  MongoDB                                                      │
│                                                               │
└───────────────────────────────────────────────────────────────┘

🚀 Final Backend Principle

Manobal-AI's backend is not designed as an autonomous surveillance or
action engine.

It is designed as a controlled AI-assisted welfare intelligence
layer:

DATA
  ↓
FEATURES
  ↓
MODEL
  ↓
SIGNAL
  ↓
CONTEXT
  ↓
HUMAN REVIEW
  ↓
WELFARE ACTION

AI should assist. Humans should decide.