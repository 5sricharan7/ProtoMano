🧠 Manobal-AI

Human-in-the-Loop Welfare Signal & Decision-Support Platform

Manobal-AI (Welfare Signal) is a full-stack decision-support workspace designed to support voluntary welfare check-ins and structured officer follow-up for personnel serving in demanding environments.

The platform analyzes authorized welfare-related signals and produces a Low / Moderate / High welfare-risk signal for human review. It is designed as a decision-support system, not an autonomous decision-maker.

Important: Manobal-AI is a demo/prototype. It is not a diagnostic system, disciplinary tool, self-harm predictor, or automated action system. Any welfare action remains subject to human review.








Built as a Smart India Hackathon 2026 prototype

📌 Overview

Personnel operating under physically demanding, psychologically stressful, or operationally challenging conditions may experience changes in workload, leave patterns, self-reported wellness, and other welfare indicators.

Manobal-AI brings voluntary welfare check-ins, model-based risk signaling, historical trend analysis, data-trust checks, and human follow-up into a single workspace.

The platform supports two primary roles

Role

Purpose

👤 Personnel

Complete voluntary welfare check-ins, view their welfare signal, review changes over time, and access the available support information

🧑‍💼 Welfare Officer

Review welfare signals, inspect supporting information, identify cases requiring attention, and record human follow-up

The current prototype uses a local browser role switch for demonstration. It does not implement production authentication or RBAC.

🎯 Problem Statement

Traditional welfare monitoring can depend heavily on manual observation and self-reporting. This can make it difficult to consistently identify changes across large populations or over time.

Manobal-AI proposes a proactive, human-centered decision-support workflow:

Voluntary Welfare Check-In
          ↓
     Weekly Records
          ↓
Canonical Feature Engineering
          ↓
       44 Features
          ↓
   Calibrated LightGBM
          ↓
 Low / Moderate / High
    Welfare Signal
          ↓
      Data Trust
          ↓
 Risk + Trust Fusion
          ↓
 REVIEW / MONITOR / VERIFY
          ↓
 Human Welfare Officer Review
          ↓
   Follow-Up / Intervention

The system is intentionally designed so that AI produces a signal while humans remain responsible for interpretation and action.

✨ Key Features

👤 Personnel

Voluntary welfare check-ins

Weekly welfare record submission

AI-powered welfare-risk signal

Low / Moderate / High signal bands

Historical welfare assessment view

Trajectory analysis

What Changed analysis

Data-trust indication

Welfare recommendations

Self-view of personal assessment history

Human-centered privacy and ethics information

🧑‍💼 Welfare Officer

Officer command workspace

Latest welfare signals across personnel

Attention-oriented case review

Historical assessment inspection

Risk + data-trust fusion

Review recommendations

Human intervention recording

Follow-up workflow

Intervention history stored in MongoDB

🤖 AI / Decision Support

Calibrated LightGBM multiclass classifier

44 numeric model features

Canonical server-side feature engineering

Class probabilities

LightGBM feature contributions when available

Data-trust heuristic

Risk + trust fusion

Historical trajectory analysis

Early-warning logic

Rule-based welfare recommendations

🧠 AI Welfare Signal

Manobal-AI uses a calibrated LightGBM multiclass classifier for welfare-risk signaling.

The current uploaded model expects 44 numeric features in a specific order defined by:

artifacts/model_metadata.json

Current model metadata:

Model Version:    0.2.0-sih-final
Feature Version:  1.1.0
Feature Count:    44

The backend loads the model artifacts at runtime and performs inference through:

POST /api/predict

The frontend does not execute the model directly.

AI inference flow

Personnel Weekly Records
          │
          ▼
   FastAPI /api/predict
          │
          ▼
Canonical Feature Engineering
          │
          ▼
      44 Features
          │
          ▼
Preprocessing Compatibility Adapter
          │
          ▼
 Calibrated LightGBM Model
          │
          ├───────────────┐
          ▼               ▼
Class Probabilities   Feature Contributions
          │               │
          └───────┬───────┘
                  ▼
             Risk Signal
                  │
                  ▼
             Data Trust
                  │
                  ▼
           Risk + Trust Fusion
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
     REVIEW    MONITOR   VERIFY DATA
                  │
                  ▼
        Human Welfare Review

📊 Welfare-Risk Bands

The model produces three welfare-risk bands:

Signal

Meaning

🟢 Low

Lower model-indicated welfare-risk signal

🟡 Moderate

Intermediate model-indicated welfare-risk signal

🔴 High

Higher model-indicated welfare-risk signal requiring human attention

These bands are signals for review, not diagnoses or definitive conclusions about an individual's condition.

🔍 Data Trust & Risk Fusion

Manobal-AI does not rely only on the raw model band.

The platform also evaluates whether the available input data appears sufficiently trustworthy for interpretation.

             MODEL RISK
                 │
                 ▼
        ┌─────────────────┐
        │   Risk Signal   │
        └────────┬────────┘
                 │
                 ├──────────────┐
                 │              │
                 ▼              ▼
          Historical Data    Data Trust
                 │              │
                 └──────┬───────┘
                        ▼
                 Risk + Trust Fusion
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
 REVIEW_RECOMMENDED   MONITOR     VERIFY_DATA

Platform-level outcomes

REVIEW_RECOMMENDED

MONITOR

VERIFY_DATA

Trajectory, early warning, What Changed, data trust, fusion, and recommendations are platform logic / heuristics. They are not additional trained models.

📈 Historical Analysis

A single assessment may not provide enough context.

Manobal-AI therefore uses stored assessment history to provide additional context to the welfare officer.

Historical analysis includes

Current Assessment
       │
       ▼
Previous Assessments
       │
       ▼
Trend / Trajectory
       │
       ├── Stable
       ├── Improving
       └── Worsening
       │
       ▼
"What Changed"
       │
       ▼
Human Review Context

The historical layer is intended to help an officer understand change over time, rather than treating one model prediction as an isolated conclusion.

💡 Welfare Recommendations

The current prototype generates welfare recommendations using rule-based platform logic.

These recommendations are not generated by a separately trained recommendation model.

Model Signal
     +
Data Trust
     +
Historical Context
     +
Platform Rules
     ↓
Welfare Recommendation

Recommendations are intended to support the officer's review process rather than automatically initiate an intervention.

🏗️ Architecture

Manobal-AI currently follows a lightweight full-stack architecture.

┌────────────────────────────────────────────────────────────┐
│                        FRONTEND                            │
│                                                            │
│              Vite + React + TypeScript                     │
│                                                            │
│                    Port 3000                               │
└───────────────────────────┬────────────────────────────────┘
                            │
                            │ REST / JSON
                            ▼
┌────────────────────────────────────────────────────────────┐
│                         BACKEND                            │
│                                                            │
│                         FastAPI                            │
│                      backend/server.py                      │
│                                                            │
│  Welfare APIs │ Prediction │ History │ Interventions       │
└───────────────┬───────────────────────────┬────────────────┘
                │                           │
                │                           ▼
                │                 ┌─────────────────────┐
                │                 │   ML Inference      │
                │                 │                     │
                │                 │ LightGBM +          │
                │                 │ Preprocessing       │
                │                 └─────────────────────┘
                │
                ▼
┌────────────────────────────────────────────────────────────┐
│                         MongoDB                            │
│                                                            │
│ Personnel │ Assessments │ Interventions │ Welfare Records   │
└────────────────────────────────────────────────────────────┘

🔄 Main User Workflow

                         MANOBAL-AI
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
         PERSONNEL                       WELFARE OFFICER
              │                               │
              ▼                               ▼
     Voluntary Check-In                 Officer Workspace
              │                               │
              ▼                               ▼
       Weekly Records                  Latest Assessments
              │                               │
              └───────────────┬───────────────┘
                              ▼
                         AI Analysis
                              │
                              ▼
                       Welfare Signal
                              │
                    ┌─────────┴─────────┐
                    ▼                   ▼
               Data Trust           History
                    │                   │
                    └─────────┬─────────┘
                              ▼
                       Risk + Trust
                          Fusion
                              │
                              ▼
                   Human Officer Review
                              │
                              ▼
                       Intervention Desk
                              │
                              ▼
                    Follow-Up Recorded

🧩 Repository Structure

ProtoMano/
│
├── artifacts/
│   ├── risk_model.pkl
│   ├── preprocessing_pipeline.pkl
│   ├── baseline_model.pkl
│   ├── model_metadata.json
│   └── MODEL_CARD.md
│
├── backend/
│   ├── server.py
│   ├── routers/
│   │   └── welfare API routes
│   ├── lib/
│   │   ├── DB client
│   │   └── InferenceEngine
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── yarn.lock
│
├── tests/
│   └── Playwright workspace
│
├── memory/
│   └── SPEC.md
│
└── README.md

📦 Model Artifacts

The following artifacts are required by the inference layer:

Artifact

Purpose

risk_model.pkl

Calibrated LightGBM multiclass classifier

preprocessing_pipeline.pkl

Runtime preprocessing transformer

baseline_model.pkl

Baseline model loaded with the inference artifacts

model_metadata.json

Ordered 44 feature names, bands, and model/feature versions

MODEL_CARD.md

Intended use, limitations, and model documentation

The artifact directory can be overridden using:

MODEL_ARTIFACT_DIR

By default, the backend expects the artifacts under:

artifacts/

🗄️ Database

Manobal-AI uses MongoDB as its persistence layer.

The platform stores information for:

Personnel
   │
   ├── Welfare Records
   │
   ├── Risk Assessments
   │
   └── Intervention History

Core collections

Personnel

Risk Assessments

Interventions

Optional welfare record collections

The model itself is loaded from serialized artifacts and is not stored inside MongoDB.

🔌 API

Local backend:

http://localhost:8001

API routes:

/api

Welfare Prediction

POST /api/predict

The endpoint accepts the personnel's raw weekly records.

The server performs the canonical feature-engineering process and derives the required 44-feature numeric vector.

Important input boundary

Raw Weekly Records
        ↓
       API
        ↓
Server-side Feature Engineering
        ↓
44 Numeric Features
        ↓
LightGBM

The API rejects pre-engineered client-supplied feature vectors.

This keeps the feature-generation process authoritative on the backend.

Demo Data

POST /api/demo/seed
GET  /api/demo/personnel

POST /api/demo/seed creates synthetic demo personnel and historical assessments using the actual uploaded model.

Other application workflows

Personnel Profile
Officer Command Workspace
Intervention Desk
History / Trajectory
Model Information

All application routes are served under /api.

🔐 Security & Ethics Boundary

Manobal-AI is explicitly designed around human oversight.

AI Model
   │
   ▼
Welfare Signal
   │
   ▼
Data Trust + Context
   │
   ▼
Human Welfare Officer
   │
   ▼
Explicit Follow-Up

The AI does NOT:

❌ Diagnose mental-health conditions
❌ Predict self-harm
❌ Make disciplinary decisions
❌ Automatically contact personnel
❌ Automatically initiate welfare action
❌ Replace welfare officers
❌ Make autonomous personnel decisions

Human-in-the-loop principle

The system provides information and signals to support human review.

AI = Decision Support
Human = Decision Maker

🧪 Synthetic Demo Data

The current prototype is trained on synthetic data.

All named personnel and organizational values displayed in the demo are synthetic and explicitly presented as DEMO DATA.

The demo seeding workflow uses the real uploaded model rather than hardcoding risk bands.

POST /api/demo/seed
        ↓
Synthetic Personnel
        ↓
Historical Records
        ↓
Real Model Inference
        ↓
Stored Assessments
        ↓
Frontend Demo

Revalidation on appropriately authorized real-world data would be required before any operational deployment.

🛠️ Technology Stack

Backend

Technology

Purpose

Python 3

Backend and ML ecosystem

FastAPI

REST API framework

Motor

Async MongoDB driver

MongoDB

Persistent data store

LightGBM

Welfare-risk classifier

scikit-learn

Preprocessing / calibration utilities

joblib

Serialized model artifacts

pytest

Backend testing

Frontend

Technology

Purpose

Vite

Frontend development/build tooling

React

User interface

TypeScript

Type-safe frontend development

Machine Learning

Component

Purpose

LightGBM

Multiclass welfare-risk classification

Preprocessing Pipeline

Runtime transformation

Calibration

Probability calibration

Feature Contributions

Model interpretability when available

Historical Heuristics

Trajectory and What Changed

Rule Engine

Welfare recommendations

⚙️ Environment Variables

Create:

backend/.env

Required

MONGO_URL=<mongodb-connection-string>
DB_NAME=<database-name>

Optional

CORS_ORIGINS=*
MODEL_ARTIFACT_DIR=../artifacts
APP_TZ=UTC
BACKEND_URL=http://localhost:8001

Do not commit secrets or production credentials.

🚀 Getting Started

Prerequisites

Install:

Python 3

pip

Node.js

Yarn

MongoDB

Git

Verify:

python --version
pip --version
node --version
yarn --version

Make sure MongoDB is running and reachable by the backend.

⚙️ Backend Setup

1. Clone the repository

git clone <repository-url>
cd ProtoMano

2. Install Python dependencies

From the backend directory:

cd backend
pip install -r requirements.txt

3. Configure MongoDB

Create:

backend/.env

Example:

MONGO_URL=mongodb://localhost:27017
DB_NAME=manobal_ai

4. Verify model artifacts

Make sure the following exist:

artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md

5. Run the backend

From backend/:

uvicorn server:app --host 0.0.0.0 --port 8001 --reload

Backend:

http://localhost:8001

🖥️ Frontend Setup

Open a new terminal:

cd frontend
yarn install

Start the development server:

yarn dev

Frontend:

http://localhost:3000

The Vite development server proxies:

/api

to:

http://localhost:8001

Run both backend and frontend together for the complete prototype.

🧪 Testing

Backend tests use the live FastAPI server.

Start the backend first:

uvicorn server:app --host 0.0.0.0 --port 8001

Then from backend/:

pytest

For a serial test run:

pytest -n 0

The current repository contains welfare prediction, demo seeding, intervention, and reliability-oriented backend tests.

The Playwright workspace is currently a scaffold; the application tests are under the backend test suite.

🔄 Development Workflow

Backend API
     │
     ▼
Model Inference
     │
     ▼
Database Integration
     │
     ▼
Personnel Workflow
     │
     ▼
Officer Workflow
     │
     ▼
Risk + Trust Fusion
     │
     ▼
Historical Analysis
     │
     ▼
Intervention Workflow
     │
     ▼
Frontend Integration
     │
     ▼
Testing & Reliability
     │
     ▼
Privacy / Ethics Review
     │
     ▼
Future Model Validation

🗺️ Roadmap

Phase 1 — Prototype Foundation

FastAPI backend

React + TypeScript frontend

MongoDB integration

Model artifact loading

/api/predict

Demo data seeding

Personnel workflow

Welfare officer workspace

Intervention recording

Phase 2 — AI Decision Support

LightGBM multiclass classifier

44-feature inference pipeline

Calibrated probabilities

Feature contributions

Data-trust heuristic

Risk + trust fusion

Historical trajectory

What Changed

Early-warning logic

Rule-based welfare recommendations

Phase 3 — Validation & Reliability

Validate on appropriately authorized real-world data

Evaluate calibration and class performance

Monitor false positives and false negatives

Evaluate subgroup performance and potential bias

Establish data-quality monitoring

Add model/version tracking

Strengthen audit logging

Conduct privacy and security review

Phase 4 — Production Readiness

Real authentication

Production RBAC

Secure session management

HTTPS

Secrets management

Rate limiting

Production monitoring

Model monitoring

Secure deployment

Formal governance and operational approval

Phase 5 — Future Expansion

Larger authorized datasets

Longitudinal modeling

Improved explainability

Better missing-data handling

Drift detection

Human feedback loops

Privacy-preserving analytics

Research-backed welfare interventions

🧱 Design Principles

1. Human-in-the-loop

AI outputs are signals for human review.

2. No autonomous welfare action

The system does not automatically initiate interventions or contact personnel.

3. Server-side inference

The canonical feature-engineering pipeline and model inference remain on the backend.

4. Data trust matters

A model signal should be interpreted alongside the quality and trustworthiness of the available data.

5. Historical context matters

The system considers changes over time rather than relying only on a single assessment.

6. Explainability

Where available, model feature contributions are surfaced to provide additional context for human reviewers.

7. Privacy by design

Welfare-related information should be collected voluntarily, handled carefully, and exposed only through appropriate authorization in a production implementation.

8. Synthetic data during prototyping

The current model and demo environment use synthetic data. Operational deployment requires separate validation.

9. AI is not a diagnosis

A welfare-risk signal must not be interpreted as a medical or psychological diagnosis.

10. Avoid unnecessary automation

The platform supports officers rather than attempting to replace human welfare processes.

🔒 Prototype Limitations

The current repository is a demo / prototype.

Known limitations include:

No production authentication

No production RBAC

Browser-based local role switch

Synthetic training data

Synthetic demo personnel

No operational deployment

No automated welfare messaging

No diagnosis

No disciplinary decision support

No self-harm prediction

No autonomous intervention

Real-world validation is still required

📈 Future Scalability

The prototype can evolve from a small demonstration into a larger welfare decision-support platform.

A future deployment could follow:

                         API Gateway
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
       Authentication     Welfare API      Officer API
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                    Decision-Support Layer
                              │
                 ┌────────────┼────────────┐
                 ▼            ▼            ▼
             ML Model     History       Data Trust
                 │            │            │
                 └────────────┼────────────┘
                              ▼
                           MongoDB

For larger populations, the system can additionally introduce:

Redis / Caching
Model Serving
Background Jobs
Observability
Audit Logging
Data Quality Monitoring
Model Drift Monitoring
Secure Cloud Deployment

The architecture should evolve according to actual requirements rather than introducing infrastructure complexity prematurely.

📊 Current Project Status

Status: Active SIH 2026 Prototype

Frontend                         ✅
FastAPI Backend                  ✅
MongoDB Integration              ✅
Model Artifact Loading           ✅
LightGBM Inference               ✅
44-Feature Pipeline              ✅
Risk Signal                      ✅
Class Probabilities              ✅
Data Trust                       ✅
Risk + Trust Fusion              ✅
Historical Trajectory            ✅
What Changed                     ✅
Welfare Recommendations          ✅
Demo Data Seeding                ✅
Officer Workspace                ✅
Intervention Recording            ✅
Production Authentication        ⏸️ Planned
Real-World Validation            ⏸️ Required
Production Deployment            ⏸️ Future

Current AI milestone

A calibrated LightGBM welfare-risk model is integrated into a human-in-the-loop decision-support workflow that combines model signals, data trust, historical context, and human officer review.

👥 User Roles at a Glance

┌──────────────────────────────────────────────────────────────┐
│                         MANOBAL-AI                           │
├──────────────────────────────┬───────────────────────────────┤
│          PERSONNEL           │        WELFARE OFFICER         │
├──────────────────────────────┼───────────────────────────────┤
│ Voluntary Check-In           │ Officer Workspace              │
│ Submit Weekly Records        │ Review Welfare Signals         │
│ Run AI Analysis              │ Inspect History                │
│ View Risk Signal             │ Review Data Trust              │
│ View History                 │ Review What Changed            │
│ View Recommendations         │ Record Intervention             │
│ Privacy / Ethics             │ Follow-Up Workflow              │
└──────────────────────────────┴───────────────────────────────┘

📚 Documentation

Project documentation is maintained within the repository.

Key areas include:

artifacts/
├── model_metadata.json
└── MODEL_CARD.md

backend/
├── server.py
├── routers/
├── lib/
└── tests/

frontend/
└── src/

memory/
└── SPEC.md

Important documentation

Model card: artifacts/MODEL_CARD.md

Model metadata: artifacts/model_metadata.json

Backend entry point: backend/server.py

Product specification: memory/SPEC.md

🛡️ Responsible AI & Ethics

Manobal-AI is intended to support human welfare processes, not automate them.

The system should be evaluated on more than predictive performance.

Important evaluation dimensions include:

Predictive Performance
        +
Calibration
        +
False Positive / False Negative Analysis
        +
Data Quality
        +
Fairness / Subgroup Evaluation
        +
Privacy
        +
Security
        +
Human Oversight
        +
Operational Safety

Before operational use, the model should be independently validated using appropriately authorized data and subjected to appropriate privacy, security, governance, and human-review procedures.

🌱 Vision

Manobal-AI aims to create a more:

Proactive. Human-centered. Privacy-aware. Explainable. Data-informed. Welfare-focused.

By combining voluntary welfare check-ins, machine-learning signals, historical context, data-trust analysis, and human officer review, the platform provides a foundation for a structured welfare-support workflow.

The goal is not to replace human judgment.

The goal is to help welfare teams notice meaningful changes earlier and make better-informed follow-up decisions.

❤️ Built for Smart India Hackathon 2026

Manobal-AI — Turning Welfare Signals into Human-Centered Support
