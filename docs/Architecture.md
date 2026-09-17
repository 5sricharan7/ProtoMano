🏗️ Manobal-AI Architecture

AI-Powered Personnel Welfare Signal & Human-in-the-Loop Decision-Support Architecture

Manobal-AI follows a modular, backend-authoritative architecture in which the frontend handles interaction, the FastAPI backend owns application logic and model inference, MongoDB stores welfare-related application data, and the ML layer produces welfare-risk signals for human review.

The architecture is intentionally designed around one principle:

                    AI = SIGNAL
                 HUMAN = DECISION

📌 Architecture Overview

┌─────────────────────────────────────────────────────────────────────┐
│                            USER LAYER                              │
│                                                                     │
│        👤 Personnel                    🧑‍💼 Welfare Officer         │
│                                                                     │
│        Voluntary Check-In             Officer Workspace             │
│        Weekly Records                 Case Review                   │
│        Personal History               Intervention Desk              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                  │
│                                                                     │
│                  Vite + React + TypeScript                          │
│                                                                     │
│  Personnel UI │ Officer UI │ Analysis │ Insights │ Ethics          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                           REST / JSON
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                             │
│                                                                     │
│                       backend/server.py                             │
│                                                                     │
│  Welfare APIs │ Prediction │ History │ Interventions │ Demo        │
└───────────────┬───────────────────────────────┬─────────────────────┘
                │                               │
                ▼                               ▼
┌──────────────────────────────┐    ┌────────────────────────────────┐
│       ML INFERENCE           │    │             MONGODB             │
│                              │    │                                │
│ Feature Engineering          │    │ Personnel                      │
│ Preprocessing                │    │ Welfare Records                │
│ LightGBM                     │    │ Risk Assessments               │
│ Calibration                 │    │ Intervention Records             │
│ Feature Contributions        │    │ Historical Data                 │
└──────────────┬───────────────┘    └────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DECISION-SUPPORT LAYER                           │
│                                                                     │
│  Risk Signal │ Data Trust │ Trajectory │ What Changed │ Rules      │
│                                                                     │
│              Risk + Trust Fusion                                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
                     HUMAN WELFARE REVIEW
                                │
                                ▼
                     FOLLOW-UP / INTERVENTION


---

# 🧭 Architectural Goals

The architecture is designed to achieve the following goals:

1. **Keep ML inference server-side**
2. **Keep business logic authoritative in the backend**
3. **Separate model prediction from platform heuristics**
4. **Provide historical context around predictions**
5. **Keep welfare actions under human control**
6. **Support future scaling without unnecessary complexity**
7. **Maintain a clear boundary between demo functionality and production requirements**

---

# 🧩 High-Level System Components

Manobal-AI consists of five major architectural layers:

```text
┌────────────────────────────────────┐
│ 1. User Interaction Layer          │
├────────────────────────────────────┤
│ 2. Frontend Application Layer      │
├────────────────────────────────────┤
│ 3. Backend Application Layer       │
├────────────────────────────────────┤
│ 4. ML / Decision-Support Layer     │
├────────────────────────────────────┤
│ 5. Persistence Layer               │
└────────────────────────────────────┘

1️⃣ User Interaction Layer

Two primary user roles interact with the prototype.

👤 Personnel

The personnel workflow provides:

Voluntary Check-In
       ↓
Weekly Welfare Records
       ↓
Run AI Analysis
       ↓
View Welfare Signal
       ↓
View History / Trajectory
       ↓
View Recommendations

🧑‍💼 Welfare Officer

The officer workflow provides:

Officer Workspace
       ↓
Latest Assessments
       ↓
Review Risk + Trust
       ↓
Inspect History
       ↓
Understand What Changed
       ↓
Human Review
       ↓
Record Intervention

The current prototype uses a local browser role switch for demonstration rather than production authentication or RBAC.

2️⃣ Frontend Architecture

The frontend is implemented using:

Vite
  +
React
  +
TypeScript

The frontend communicates with the backend using relative API paths:

/api/...

The Vite development server proxies these requests to:

http://localhost:8001

Frontend flow

React UI
   │
   ▼
Frontend API Request
   │
   ▼
/api/...
   │
   ▼
Vite Proxy
   │
   ▼
FastAPI

The frontend does not execute the ML model.

3️⃣ Backend Architecture

The backend is implemented using FastAPI.

Main entry point:

backend/server.py

The backend acts as the central application authority.

It is responsible for:

API routing

Input validation

Welfare workflows

Model inference orchestration

Feature engineering

Data persistence

Historical assessment retrieval

Intervention recording

Demo data seeding

Model information

Backend flow

HTTP Request
     │
     ▼
FastAPI Route
     │
     ▼
Validation
     │
     ▼
Application Logic
     │
     ├───────────────┐
     ▼               ▼
 ML Inference     MongoDB
     │               │
     └───────┬───────┘
             ▼
        API Response

4️⃣ ML / Decision-Support Architecture

The ML system has a strict separation between:

TRAINED MODEL
      vs.
PLATFORM LOGIC

Trained components

Preprocessing Pipeline
        +
Calibrated LightGBM
        +
Feature Contributions

Platform components

Data Trust
Trajectory
Early Warning
What Changed
Risk + Trust Fusion
Welfare Recommendations

The platform does not treat these heuristics as additional trained models.

🧠 Model Inference Architecture

The current model expects:

44 numerical features

in the exact order defined by:

artifacts/model_metadata.json

The current metadata specifies:

Model Version:    0.2.0-sih-final
Feature Version:  1.1.0
Feature Count:    44

Complete inference flow

                    RAW DATA
                       │
                       ▼
              Weekly Welfare Records
                       │
                       ▼
                 POST /api/predict
                       │
                       ▼
             Server-Side Validation
                       │
                       ▼
          Canonical Feature Engineering
                       │
                       ▼
              44 Ordered Features
                       │
                       ▼
          Preprocessing Compatibility
                 Adapter / Pipeline
                       │
                       ▼
              Calibrated LightGBM
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
      Class Probabilities   Feature Contributions
             │                   │
             └─────────┬─────────┘
                       ▼
                Welfare Signal
                       │
              ┌────────┼────────┐
              ▼        ▼        ▼
             LOW    MODERATE    HIGH

🔐 Why Feature Engineering Is Server-Side

The frontend sends:

raw_records

rather than a pre-engineered feature vector.

The backend then performs:

Raw Records
    ↓
Canonical Feature Engineering
    ↓
44 Features
    ↓
Model

Pre-engineered client-supplied vectors are rejected.

This provides:

Consistent feature generation

Correct feature ordering

Reduced client-side manipulation

One authoritative inference pipeline

Easier model version management

🔍 Decision-Support Layer

The model output is passed into a second layer that provides context.

                  MODEL
                    │
                    ▼
              Risk Signal
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    Data Trust    History    What Changed
        │           │           │
        └───────────┼───────────┘
                    ▼
             Risk + Trust Fusion
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       REVIEW    MONITOR   VERIFY DATA

This layer is not another ML model.

It is application-level decision-support logic.

📊 Risk Signal Layer

The ML classifier produces:

LOW
MODERATE
HIGH

The signal represents model-indicated welfare risk.

It is not:

❌ A diagnosis
❌ A psychological assessment
❌ A disciplinary classification
❌ A self-harm prediction
❌ An autonomous decision

🧪 Data Trust Layer

The platform evaluates the quality and trustworthiness of the available input data.

Conceptually:

Input Data
    │
    ▼
Data Completeness / Consistency
    │
    ▼
Data Trust Heuristic
    │
    ▼
Interpretation Context

The resulting trust information is combined with the model signal.

Risk Signal + Data Trust
          ↓
   Contextual Result

Possible platform outcomes include:

REVIEW_RECOMMENDED
MONITOR
VERIFY_DATA

📈 Historical Context Layer

MongoDB stores previous assessments.

The historical layer retrieves those assessments and derives:

Current Assessment
       +
Previous Assessments
       ↓
Historical Timeline
       ↓
Trajectory
       ↓
Early-Warning Logic
       ↓
What Changed

Important architectural distinction

Historical trajectory and early-warning calculations are platform logic, not separate trained models.

🔄 What Changed Architecture

The “What Changed” component compares relevant information between assessment periods.

Previous Period
      │
      ▼
Historical Features
      │
      │
      ▼
Current Period
      │
      ▼
Current Features
      │
      └──────────────┐
                     ▼
                Comparison
                     │
                     ▼
              Meaningful Changes
                     │
                     ▼
              Officer Context

This provides contextual information around the current signal.

💡 Recommendation Layer

The current prototype uses rule-based welfare recommendations.

Risk Signal
     +
Data Trust
     +
Historical Context
     +
Platform Rules
     ↓
Welfare Recommendation

The recommendation layer does not independently diagnose or make personnel decisions.

🗄️ Persistence Architecture

MongoDB acts as the application's persistence layer.

┌──────────────────────────────────────┐
│              MONGODB                 │
├──────────────────────────────────────┤
│ Personnel                            │
│ Welfare Records                      │
│ Risk Assessments                     │
│ Intervention Records                 │
│ Historical Assessments               │
└──────────────────────────────────────┘

Logical relationships

Personnel
   │
   ├── Welfare Records
   │
   ├── Risk Assessments
   │
   └── Interventions

🧑‍💼 Intervention Architecture

Interventions remain outside autonomous model execution.

Model
 │
 ▼
Signal
 │
 ▼
Officer Workspace
 │
 ▼
Human Review
 │
 ▼
Officer Decision
 │
 ▼
Intervention Desk
 │
 ▼
MongoDB

The ML model cannot directly execute a welfare intervention.

🌐 API Architecture

The major API boundary is:

Frontend
    │
    ▼
/api
    │
    ▼
FastAPI

Core endpoints

POST /api/predict

Runs model inference from raw weekly records.

POST /api/demo/seed

Creates synthetic demonstration records and historical assessments.

GET /api/demo/personnel

Retrieves demo personnel and stored assessment history.

GET /api/model-info

Provides model/artifact information.

Other application routes support:

Personnel
Officer Workspace
History
Interventions
Welfare Records

📦 Model Artifact Architecture

The inference layer loads serialized artifacts from:

artifacts/

artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md

Runtime flow

FastAPI Startup
      │
      ▼
InferenceEngine
      │
      ├── risk_model.pkl
      ├── preprocessing_pipeline.pkl
      ├── baseline_model.pkl
      └── model_metadata.json
      │
      ▼
Ready for /api/predict

The artifact directory can be configured through:

MODEL_ARTIFACT_DIR

🧩 Repository Architecture

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
│   │
│   ├── routers/
│   │   └── Welfare API Routes
│   │
│   ├── lib/
│   │   ├── DB Client
│   │   └── InferenceEngine
│   │
│   ├── tests/
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── yarn.lock
│
├── tests/
│   └── Playwright Workspace
│
├── memory/
│   └── SPEC.md
│
└── README.md

🔐 Security Boundary

The architecture intentionally keeps sensitive operations on the backend.

                    FRONTEND
                       │
                       │ User Input
                       ▼
                  FASTAPI API
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
        Application          ML Inference
          Logic                   │
             │                    ▼
             │              Risk Signal
             │                    │
             └─────────┬──────────┘
                       ▼
                    MongoDB

The frontend is not trusted with:

Model execution

Canonical feature generation

Database access

Direct intervention execution

Authoritative welfare calculations

🛡️ Human Oversight Boundary

The most important architectural boundary is:

                AI SYSTEM
                    │
                    ▼
              WELFARE SIGNAL
                    │
                    ▼
          CONTEXT + DATA TRUST
                    │
                    ▼
             HUMAN OFFICER
                    │
                    ▼
              HUMAN REVIEW
                    │
                    ▼
             FOLLOW-UP ACTION

The system intentionally stops before autonomous welfare action.

🔄 Complete End-to-End Architecture

                         ┌───────────────┐
                         │   PERSONNEL   │
                         └───────┬───────┘
                                 │
                         Voluntary Data
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         REACT FRONTEND                          │
│                    Vite + React + TypeScript                    │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                              REST
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FASTAPI BACKEND                         │
│                                                                 │
│ Validation │ Welfare APIs │ History │ Interventions │ Demo      │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
               ▼                              ▼
┌──────────────────────────┐       ┌──────────────────────────────┐
│      ML INFERENCE        │       │           MONGODB             │
│                          │       │                              │
│ Feature Engineering      │       │ Personnel                    │
│ Preprocessing            │       │ Welfare Records              │
│ Calibrated LightGBM      │       │ Risk Assessments             │
│ Probabilities            │       │ Interventions                │
│ Feature Contributions    │       │ Historical Data              │
└──────────────┬───────────┘       └──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DECISION-SUPPORT LOGIC                         │
│                                                                 │
│ Data Trust │ Trajectory │ What Changed │ Early Warning          │
│                                                                 │
│                    Risk + Trust Fusion                          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ WELFARE OFFICER │
                       │                 │
                       │ Human Review    │
                       └────────┬────────┘
                                │
                                ▼
                       Intervention Desk
                                │
                                ▼
                             MongoDB

⚡ Why This Architecture?

1. Backend as the source of truth

The backend controls:

Feature engineering

Model inference

Welfare records

Historical assessments

Intervention records

2. Model isolation

The ML artifacts are isolated from the frontend and loaded through the backend inference engine.

3. Clear separation of concerns

Frontend
   → Presentation

FastAPI
   → Application Logic

ML Layer
   → Prediction

MongoDB
   → Persistence

Decision-Support Layer
   → Context / Heuristics

Human Officer
   → Final Welfare Decision

4. Human-centered design

The architecture prevents the model from becoming an autonomous action system.

5. Future scalability

The current modular structure can later support:

Authentication Service
       │
       ▼
Welfare Service
       │
       ▼
ML Model Service
       │
       ▼
Data / Analytics Layer
       │
       ▼
Monitoring & Audit

without requiring the prototype to begin with unnecessary microservice complexity.

🚀 Future Production Architecture

The prototype can evolve toward:

                         API Gateway
                              │
             ┌────────────────┼────────────────┐
             │                │                │
             ▼                ▼                ▼
       Authentication     Welfare API     Officer API
             │                │                │
             └────────────────┼────────────────┘
                              │
                              ▼
                    Decision-Support Layer
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          ML Serving       History         Data Trust
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                           Database
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
             Monitoring                Audit Logs

Potential production infrastructure:

Redis
Background Workers
Model Serving
Observability
Audit Logging
Data Quality Monitoring
Model Drift Detection
Secure Cloud Infrastructure

🧪 Prototype vs Production

Component

Current Prototype

Production Direction

Authentication

Local role switch

Secure authentication

RBAC

Not implemented

Production RBAC

Database

MongoDB

Hardened managed database

ML

Serialized LightGBM

Versioned model serving

Data

Synthetic

Authorized validated data

Inference

FastAPI process

Dedicated/scalable serving if required

Monitoring

Basic

Full observability

Audit

Limited

Comprehensive audit trail

Security

Prototype-level

Security-reviewed deployment

Welfare Action

Human-led

Governed human-led workflow

🧱 Architectural Design Principles

1. AI is a signal generator

The model provides a welfare-risk signal rather than an autonomous decision.

2. Human review is mandatory

The welfare officer remains responsible for interpreting the signal and determining appropriate follow-up.

3. Server-side inference

Feature engineering and ML inference remain on the backend.

4. One canonical feature pipeline

The same feature ordering defined by model metadata is preserved during inference.

5. Platform logic is separated from ML

Trajectory, data trust, early warning, and recommendations are not represented as additional trained models.

6. Database-backed history

Historical assessments are persisted so that current signals can be interpreted over time.

7. Privacy-aware design

Sensitive welfare information should be protected through access control, minimization, secure storage, and appropriate retention policies in production.

8. Prototype transparency

Synthetic data, local role switching, and other prototype limitations are explicitly separated from production capabilities.

9. Avoid premature complexity

The architecture can scale later without introducing microservices, queues, or distributed infrastructure before they are actually needed.

📊 Architecture Summary

┌────────────────────────────────────────────────────┐
│                    MANOBAL-AI                      │
├────────────────────────────────────────────────────┤
│                                                    │
│  React + TypeScript                                │
│           ↓                                        │
│  FastAPI Backend                                   │
│           ↓                                        │
│  Feature Engineering                               │
│           ↓                                        │
│  44-Feature Pipeline                               │
│           ↓                                        │
│  Calibrated LightGBM                              │
│           ↓                                        │
│  Welfare-Risk Signal                              │
│           ↓                                        │
│  Data Trust + Historical Context                  │
│           ↓                                        │
│  Risk + Trust Fusion                              │
│           ↓                                        │
│  Human Welfare Officer                            │
│           ↓                                        │
│  Follow-Up / Intervention                         │
│           ↓                                        │
│  MongoDB                                          │
│                                                    │
└────────────────────────────────────────────────────┘

Manobal-AI is architected so that machine learning provides evidence and context, while human welfare personnel retain responsibility for interpretation and action.