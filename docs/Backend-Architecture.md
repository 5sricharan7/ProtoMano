<div align="center">

# ⚙️ Manobal-AI — Backend Architecture

### AI-Assisted Welfare Signal & Human-in-the-Loop Decision Support Backend

<p>
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/MongoDB-Persistence-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB"/>
  <img src="https://img.shields.io/badge/LightGBM-ML%20Inference-2E8B57?style=for-the-badge" alt="LightGBM"/>
</p>

<p>
  <img src="https://img.shields.io/badge/Pydantic-Validation-E92063?style=flat-square" alt="Pydantic"/>
  <img src="https://img.shields.io/badge/Motor-MongoDB%20Driver-47A248?style=flat-square" alt="Motor"/>
  <img src="https://img.shields.io/badge/Uvicorn-ASGI-499848?style=flat-square" alt="Uvicorn"/>
  <img src="https://img.shields.io/badge/Pytest-Testing-0A9EDC?style=flat-square&logo=pytest&logoColor=white" alt="Pytest"/>
</p>

> **AI should assist. Humans should decide.**

</div>

---

## 📌 1. Backend Overview

Manobal-AI is a welfare-oriented decision-support platform designed for uniformed personnel.

Its backend is responsible for:

- Secure and controlled data handling
- Canonical feature engineering
- Machine-learning inference
- Historical assessment analysis
- Data-trust evaluation
- Risk/trust fusion
- Welfare-oriented recommendations
- Recording human-reviewed interventions

The backend is built with **FastAPI** and acts as the central application and inference layer between the React frontend, MongoDB, and serialized machine-learning artifacts.

### Core Architectural Principle

```text
┌──────────────────────────────────────────────┐
│                                              │
│              🤖 AI = SIGNAL                  │
│                                              │
│                    ↓                         │
│                                              │
│           🧑‍💼 HUMAN = DECISION              │
│                                              │
└──────────────────────────────────────────────┘
```

The backend is therefore designed to provide **evidence and context**, while keeping welfare follow-up under human control.

---

# 🧭 2. Backend Responsibilities

The backend follows a clear separation of responsibilities:

| Layer | Responsibility |
|---|---|
| 🌐 API Layer | Exposes REST endpoints and handles HTTP communication |
| 🛡️ Validation Layer | Validates requests and rejects unsupported inputs |
| 🧩 Feature Engineering | Converts raw weekly records into canonical 44-feature input |
| 🧠 ML Inference | Loads preprocessing/model artifacts and generates risk probabilities |
| 🔍 Decision Support | Combines model output with trust and historical context |
| 📈 Historical Intelligence | Analyzes previous assessments and trajectory |
| 💡 Recommendation | Generates rule-based welfare-oriented recommendations |
| 🗄️ Persistence | Stores personnel, assessments and intervention/review records |
| 🧑‍💼 Human Oversight | Keeps the welfare officer in control of follow-up actions |

---

# 🏗️ 3. High-Level Backend Architecture

```text
                         ┌──────────────────────────┐
                         │      React Frontend      │
                         │     Vite + TypeScript    │
                         └────────────┬─────────────┘
                                      │
                              REST / JSON APIs
                                      │
                                      ▼
                    ┌──────────────────────────────────┐
                    │         ⚡ FastAPI Backend        │
                    │                                  │
                    │ API Routes / Request Validation  │
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
                         │ 🧑‍💼 Human Review   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │ Intervention /     │
                         │ Follow-up Record   │
                         └─────────┬──────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
                         │      MongoDB       │
                         └────────────────────┘
```

---

# 🎯 4. Backend Design Goals

## 🔹 4.1 Secure Data Processing

Personnel welfare data should remain within the controlled backend boundary instead of being processed directly inside the browser.

```text
Browser
   │
   ▼
Controlled API
   │
   ▼
Backend
   │
   ├── Validation
   ├── Feature Engineering
   ├── ML Inference
   └── Persistence
```

---

## 🔹 4.2 Canonical ML Input

The frontend sends **raw weekly records**.

The backend derives the model input using the canonical feature-engineering pipeline.

```text
Raw Records
     ↓
Server-Side Feature Engineering
     ↓
Canonical 44-Feature Vector
     ↓
Preprocessing
     ↓
LightGBM
```

This prevents clients from manually supplying arbitrary pre-engineered model vectors.

---

## 🔹 4.3 Explainable Decision Support

The backend does not return only a prediction.

It can combine:

- Calibrated class probabilities
- Model feature contributions when available
- Data-trust information
- Historical trajectory
- Change detection
- Risk/trust fusion
- Welfare-oriented recommendations

```text
Model Output
     +
Data Trust
     +
Historical Context
     +
Observed Changes
     ↓
Contextual Decision Support
```

---

## 🔹 4.4 Human-in-the-Loop Operation

The backend provides signals to a welfare officer rather than autonomously taking welfare or disciplinary action.

```text
AI Analysis
     ↓
Risk Signal
     ↓
Decision Support
     ↓
Human Review
     ↓
Follow-Up / Intervention
```

---

## 🔹 4.5 Modular Architecture

API routing, inference, feature engineering, database operations, historical intelligence, and decision-support logic remain separate responsibilities.

This allows the backend to evolve without rewriting the complete application.

---

# 🧰 5. Backend Technology Stack

| Layer | Technology |
|---|---|
| Backend Framework | **FastAPI** |
| Language | **Python** |
| Database | **MongoDB** |
| MongoDB Driver | **Motor** |
| API Format | **REST / JSON** |
| ML Model | **Calibrated LightGBM** |
| Preprocessing | **Serialized preprocessing pipeline** |
| Validation / Schemas | **Pydantic** |
| Server | **Uvicorn** |
| Testing | **Pytest** |
| Configuration | **Environment variables / `.env`** |
| Frontend Consumer | **React + Vite + TypeScript** |

---

# 🧩 6. Backend Layer Architecture

The backend can be understood as six logical layers:

```text
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
```

### Layer Contract

```text
API
 ↓
Validation
 ↓
Domain / Feature Engineering
 ↓
Inference
 ↓
Decision Support
 ↓
Persistence
```

The logical layers are separated by responsibility even where the current prototype keeps implementation relatively compact.

---

# 🌐 7. API Layer

FastAPI provides the HTTP interface consumed by the React frontend.

The API layer is responsible for:

- Receiving requests
- Validating payloads
- Calling application logic
- Returning structured JSON responses
- Handling errors
- Keeping model execution on the server

### Request Boundary

```text
React Frontend
      │
      │ REST / JSON
      ▼
FastAPI
      │
      ▼
Application Services
```

The frontend does **not** execute the LightGBM model.

---

# 🔄 8. Core Backend Request Flow

A typical AI-analysis request follows this sequence:

```text
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
```

---

# 🧪 9. Request Validation

Validation occurs before model inference.

```text
Incoming Request
       │
       ▼
Pydantic / Request Validation
       │
       ├── Valid ──────► Feature Engineering
       │
       └── Invalid ────► Error Response
```

The validation boundary helps ensure that unsupported input structures do not reach the inference pipeline.

---

# 🧩 10. Server-Side Feature Engineering

One of the most important backend design decisions is that feature engineering is performed on the server.

The client submits raw weekly welfare records rather than a precomputed ML vector.

### Feature Engineering Flow

```text
Raw Weekly Records
        │
        ▼
Backend Feature Engineering
        │
        ├── Aggregate Signals
        ├── Temporal Features
        ├── Workload Indicators
        ├── Leave / Activity Indicators
        └── Other Canonical Transformations
        │
        ▼
44 Numeric Features
        │
        ▼
Model Preprocessing
        │
        ▼
LightGBM
```

### Why this matters

This architecture:

- Centralizes feature definitions
- Reduces client-side manipulation
- Preserves training/inference consistency
- Makes model upgrades easier
- Prevents arbitrary pre-engineered vectors from being submitted by the UI

The backend rejects unsupported pre-engineered client vectors and expects the canonical raw-record format.

---

# 🔢 11. 44-Feature Inference Contract

The current model expects **44 numeric features in a specific order**.

The ordering is controlled through:

```text
artifacts/model_metadata.json
```

The backend therefore treats model metadata as part of the inference contract.

```text
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
```

### Why the contract matters

A vector can be numerically valid while still being semantically incorrect if feature ordering changes.

The canonical feature contract therefore protects against silent inference mismatches.

---

# 🧠 12. ML Inference Layer

The ML layer loads serialized artifacts from the configured artifact directory.

## Current Artifacts

```text
artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md
```

## Current Model Metadata

```text
Model Version:   0.2.0-sih-final
Feature Version: 1.1.0
Input Features:  44 numeric features
Model:           Calibrated LightGBM
```

The artifact directory can be configured through:

```text
MODEL_ARTIFACT_DIR
```

---

# 🔬 13. Inference Pipeline

The complete inference pipeline is:

```text
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
```

---

# 📊 14. Risk Signal Layer

The ML model generates a calibrated risk signal rather than directly deciding what action should be taken.

The backend can expose:

- Predicted risk class
- Calibrated class probabilities
- Relevant feature contributions
- Contextual information required by the dashboard

### Architectural Boundary

```text
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
Welfare Follow-Up
```

The model does not directly trigger:

- ❌ Disciplinary action
- ❌ Automated welfare intervention
- ❌ Autonomous personnel decisions

---

# 🛡️ 15. Data Trust Layer

Risk output is interpreted together with a data-trust heuristic.

The purpose is to distinguish between:

```text
Meaningful / sufficiently supported signal
                vs.
Potentially unreliable or incomplete data
```

### Conceptual Flow

```text
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
```

Possible platform states include:

```text
REVIEW_RECOMMENDED
MONITOR
VERIFY_DATA
```

These states are **decision-support outputs**, not additional trained ML models.

---

# 🔀 16. Risk + Trust Fusion

The backend does not treat model probability as the entire decision context.

Instead:

```text
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
```

This allows the welfare officer to distinguish between:

- A meaningful risk signal
- A signal that should be monitored
- A case where underlying data should first be verified

---

# 📈 17. Historical Intelligence Layer

The backend maintains historical assessment context in MongoDB.

Historical records allow the platform to analyze:

- Previous risk assessments
- Changes over time
- Trajectory
- Historical patterns
- Recent deviations

### Historical Flow

```text
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
```

The current assessment is therefore interpreted in relation to previous observations rather than treated as an isolated prediction.

---

# 🔄 18. “What Changed” Layer

The backend can derive a human-readable view of meaningful changes between current data and historical context.

```text
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
```

This provides contextual information around the current signal instead of presenting only a risk label.

---

# 💡 19. Welfare Recommendation Layer

Recommendations are generated through platform logic and rules.

They are **not another trained predictive model**.

```text
Risk Signal
    +
Data Trust
    +
Historical Context
    +
Observed Changes
    ↓
Welfare Recommendations
```

The purpose is to help the officer understand what type of follow-up may be appropriate.

The final action remains with the authorized human reviewer.

---

# 🧑‍💼 20. Human-in-the-Loop Architecture

Human oversight is a core backend boundary.

```text
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
          Monitor /       Follow-up /
          No Action       Intervention
                              │
                              ▼
                     Intervention Record
                              │
                              ▼
                          MongoDB
```

The backend records human review rather than allowing the model to autonomously execute welfare actions.

---

# 📝 21. Intervention Architecture

Interventions represent the human-reviewed response to an AI-assisted signal.

```text
AI Assessment
      │
      ▼
Officer Review
      │
      ├── Review Decision
      ├── Follow-Up Details
      └── Intervention Information
      │
      ▼
Intervention API
      │
      ▼
MongoDB
```

### Critical distinction

```text
Model Output ≠ Human Decision
```

The backend therefore maintains a clear boundary between prediction and action.

---

# 🗄️ 22. MongoDB Persistence Architecture

MongoDB is used as the backend persistence layer.

The backend stores application information such as:

- Personnel profiles
- Welfare-related records
- Risk assessments
- Historical assessments
- Intervention / review records
- Synthetic demo records

### Logical Structure

```text
MongoDB
│
├── Personnel
│   └── Profile / Context
│
├── Assessments
│   ├── Current Result
│   ├── Probabilities
│   ├── Trust Information
│   └── Historical Assessment Data
│
├── Interventions
│   ├── Human Review
│   └── Follow-Up Information
│
└── Demo / Welfare Records
    └── Synthetic Prototype Data
```

---

# 📚 23. Historical Assessment Persistence

Every assessment can contribute to a personnel-level historical context.

```text
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
```

This supports trajectory-based decision support without requiring the frontend to reconstruct history itself.

---

# 🌱 24. Demo Data Architecture

The prototype includes a controlled synthetic-data workflow.

```text
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
```

The demo workflow demonstrates the complete backend architecture without requiring operational personnel data.

---

# 🌐 25. API Architecture

The backend exposes API routes under:

```text
/api
```

### Functional Areas

```text
/api/predict
/api/demo/seed
/api/demo/personnel
/api/interventions
```

The exact route organization is maintained inside the backend router structure.

---

## `POST /api/predict`

### Purpose

- Receive raw weekly records
- Perform server-side feature engineering
- Run the trained model
- Generate risk probabilities
- Evaluate data trust
- Incorporate historical context
- Return decision-support information

```text
POST /api/predict
        │
        ▼
Validation
        │
        ▼
Feature Engineering
        │
        ▼
ML Inference
        │
        ▼
Decision Support
        │
        ▼
JSON Response
```

---

## `POST /api/demo/seed`

### Purpose

- Create synthetic demonstration personnel
- Generate historical assessment context
- Run the actual uploaded model
- Populate the prototype database

---

## `GET /api/demo/personnel`

### Purpose

- Retrieve synthetic personnel profiles
- Retrieve historical assessment context
- Support the demonstration interface

---

## `/api/interventions`

### Purpose

Record human-reviewed welfare follow-up / intervention information.

---

# 📁 26. Backend Repository Architecture

The backend is organized as a modular Python application.

```text
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
```

The repository also contains:

```text
artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md
```

---

# ⚙️ 27. Configuration Architecture

The backend uses environment-based configuration.

### Configuration Variables

```text
MONGO_URL=
DB_NAME=
CORS_ORIGINS=
MODEL_ARTIFACT_DIR=
APP_TZ=
BACKEND_URL=
```

| Variable | Requirement |
|---|---|
| `MONGO_URL` | Required |
| `DB_NAME` | Required |
| `CORS_ORIGINS` | Optional |
| `MODEL_ARTIFACT_DIR` | Optional |
| `APP_TZ` | Optional |
| `BACKEND_URL` | Optional |

Keeping configuration outside application code makes deployment and environment changes easier.

---

# 🔗 28. CORS & Frontend Communication

The frontend communicates with backend endpoints using relative `/api/...` paths.

```text
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
```

CORS behavior can be configured through:

```text
CORS_ORIGINS
```

---

# 🔐 29. Backend Security Boundary

The architecture intentionally keeps sensitive processing on the server.

```text
┌────────────────────────────────────┐
│            Frontend                │
│                                    │
│ UI + Request Composition           │
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
```

The browser does not directly access:

- ❌ Serialized ML models
- ❌ Preprocessing artifacts
- ❌ Database credentials
- ❌ MongoDB
- ❌ Internal feature-engineering logic

---

# 🛡️ 30. Responsible AI Boundary

Manobal-AI is designed as a welfare decision-support system, not an autonomous authority.

| Capability | Backend Role |
|---|---|
| Welfare signal | ✅ Generate AI-assisted signal |
| Diagnosis | ❌ Not performed |
| Automatic discipline | ❌ Not performed |
| Automatic welfare action | ❌ Not performed |
| Officer review | ✅ Required |
| Historical context | ✅ Supported |
| Data-trust evaluation | ✅ Supported |
| Human-reviewed intervention record | ✅ Supported |
| Synthetic demo data | ✅ Supported |

---

# 🧠 31. Model vs Platform Logic

A major architectural distinction is maintained between trained ML components and platform decision-support logic.

## Trained Components

```text
Preprocessing Pipeline
        +
Calibrated LightGBM Model
```

## Platform Logic

```text
Feature Engineering
Data Trust Heuristic
Historical Trajectory
"What Changed"
Risk + Trust Fusion
Welfare Recommendations
```

This separation makes the architecture easier to explain, validate, test, and improve.

---

# 🔄 32. End-to-End Backend Architecture

```text
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
```

---

# ⚡ 33. Why This Backend Architecture?

## 1. Backend as the Source of Truth

The backend controls:

```text
Feature Engineering
Model Inference
Welfare Records
Historical Assessments
Intervention Records
```

## 2. Model Isolation

```text
Frontend
   │
   ▼
FastAPI
   │
   ▼
InferenceEngine
   │
   ▼
ML Artifacts
```

The frontend never needs direct access to model artifacts.

## 3. Clear Separation of Concerns

```text
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
```

## 4. Human-Centered Design

```text
AI
 ↓
Signal
 ↓
Context
 ↓
Human Review
 ↓
Action
```

## 5. Future Scalability

The architecture can later support:

```text
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
```

without requiring the prototype to begin with unnecessary microservice complexity.

---

# 🚀 34. Future Production Architecture

The backend can evolve toward a more hardened production architecture:

```text
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
```

### Potential Production Infrastructure

```text
Redis
Background Workers
Dedicated Model Serving
Observability
Audit Logging
Data Quality Monitoring
Model Drift Detection
Secure Cloud Infrastructure
```

These are **architectural directions**, not claims that all components are currently implemented.

---

# 🧪 35. Prototype vs Production Backend

| Area | Current Prototype | Production Direction |
|---|---|---|
| Authentication | Demo role switch | Enterprise authentication + RBAC |
| Database | MongoDB | Hardened managed deployment |
| Data | Synthetic demo data | Authorized operational data |
| ML | Serialized LightGBM artifact | Revalidated/versioned model serving |
| API | FastAPI REST | Hardened API/service deployment |
| Secrets | Environment configuration | Managed secret infrastructure |
| Auditability | Intervention records | Immutable audit logging |
| Monitoring | Development/test setup | Production observability |
| Deployment | Local/prototype | Containerized cloud/on-prem deployment |
| Welfare Action | Human-led | Governed human-led workflow |

> These production items are architectural directions, not claims that they are already implemented.

---

# 🧪 36. Testing Architecture

Backend tests are maintained under:

```text
backend/tests/
```

The project uses:

```text
pytest
```

Run tests with:

```bash
pytest
```

For serial execution:

```bash
pytest -n 0
```

The test architecture is intended to validate:

- API behavior
- Inference flow
- Request validation
- Feature engineering
- Backend logic
- Persistence behavior
- Integration behavior

---

# ▶️ 37. Backend Startup

From the backend directory:

```bash
cd backend
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start FastAPI:

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

The backend is then available for frontend API communication.

---

# 📊 38. Backend Data Flow Summary

```text
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
```

---

# 🧱 39. Backend Architecture Principles

### 1. Server-Side Inference

ML inference remains inside the backend.

### 2. Canonical Feature Pipeline

Raw records are transformed into the official 44-feature representation on the server.

### 3. Separation of Concerns

API, database, ML, feature engineering, and decision-support responsibilities remain modular.

### 4. Human-in-the-Loop

AI output is presented for human review rather than autonomous action.

### 5. Context Over Isolated Prediction

Current signals are interpreted alongside historical information and data trust.

### 6. Transparent AI

The system exposes probabilities, relevant contributions when available, and supporting context.

### 7. Privacy-Oriented Design

Database and model artifacts remain behind the backend boundary.

### 8. Production-Aware Architecture

The prototype is structured so authentication, RBAC, auditing, observability, and secure deployment can be added later.

---

# 📋 40. Backend Architecture at a Glance

| Component | Responsibility |
|---|---|
| **FastAPI** | Backend API and application server |
| **Pydantic** | Request / response validation |
| **Feature Engineering** | Raw records → 44 canonical features |
| **Preprocessing Pipeline** | ML input transformation |
| **LightGBM** | Welfare-risk classification |
| **Data Trust** | Input reliability heuristic |
| **Historical Intelligence** | Trajectory and historical context |
| **Risk + Trust Fusion** | Contextual decision-support state |
| **Recommendations** | Rule-based welfare guidance |
| **MongoDB** | Persistent application data |
| **Intervention API** | Human-reviewed follow-up records |
| **Pytest** | Backend testing |
| **Uvicorn** | ASGI server |

---

# 🏁 41. Final Backend Architecture

```text
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
```

---

# 🎯 42. Final Backend Principle

Manobal-AI's backend is not designed as an autonomous surveillance or action engine.

It is designed as a controlled **AI-assisted welfare intelligence layer**:

```text
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
```

> ## 🤖 AI should assist.
> ## 🧑‍💼 Humans should decide.

---

<div align="center">

### ⚙️ Backend Architecture

**FastAPI · LightGBM · MongoDB · Human-in-the-Loop**

**AI-Assisted • Evidence-Aware • Human-Led**

</div>
