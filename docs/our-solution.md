<div align="center">

# 🧠 Manobal-AI

### AI-Powered Personnel Welfare Signal & Human-in-the-Loop Decision-Support Platform

<p>
  <strong>Smart India Hackathon 2026 • Problem Statement 26186</strong>
</p>

<p>
  A privacy-aware, human-centered prototype for identifying meaningful personnel welfare signals earlier through voluntary check-ins, structured organizational data, machine-learning analysis, historical context, and human-led follow-up.
</p>

</div>

---

## 📌 Overview

Personnel serving in CAPFs, Armed Forces, and other uniformed services can operate under demanding conditions involving extended deployments, irregular duty schedules, workload pressure, transfers, training commitments, family separation, and other operational challenges.

The SIH problem statement calls for an AI-powered personnel stress and welfare monitoring system capable of identifying early indicators while protecting **privacy, confidentiality, dignity, and organizational trust**.

Manobal-AI addresses this through a human-in-the-loop welfare workflow:

```text
Voluntary Welfare Check-In
          ↓
Organizational / Wellness Signals
          ↓
Server-Side Feature Engineering
          ↓
44-Feature ML Pipeline
          ↓
Calibrated LightGBM
          ↓
LOW / MODERATE / HIGH
Welfare-Risk Signal
          ↓
Data Trust + Historical Context
          ↓
Risk + Trust Fusion
          ↓
REVIEW / MONITOR / VERIFY DATA
          ↓
Authorized Human Review
          ↓
Follow-Up / Intervention
```

> **Core principle:** AI produces a signal. An authorized human makes the decision.

Manobal-AI is intentionally designed as **decision support**, not autonomous personnel decision-making.

---

## 🎯 Problem Statement

### The Challenge

Welfare concerns may emerge gradually through changes in:

- Workload
- Leave patterns
- Deployment conditions
- Duty schedules
- Transfer frequency
- Training commitments
- Voluntary wellness assessments
- Other authorized wellness indicators

Traditional identification can depend heavily on manual observation and self-reporting. At larger scale, this can make it difficult to consistently identify meaningful changes over time and prioritize cases that may warrant human attention.

### The Core Gap

```text
Operational & Welfare Data
            │
            ▼
       Personnel
            │
            ▼
 ┌──────────────────────┐
 │ Manual Observation   │
 │         +            │
 │ Self-Reporting       │
 └──────────┬───────────┘
            │
            ▼
      Limited Scale
            │
            ▼
 Difficulty Identifying
 Meaningful Changes Early
```

---

# 💡 Our Solution — Manobal-AI

Manobal-AI converts authorized and voluntarily provided welfare information into structured welfare signals and contextual insights for human review.

```text
                         MANOBAL-AI
                              │
              ┌───────────────┴───────────────┐
              │                               │
              ▼                               ▼
          PERSONNEL                     WELFARE OFFICER
              │                               │
              ▼                               ▼
      Voluntary Check-In               Officer Workspace
              │                               │
              └───────────────┬───────────────┘
                              ▼
                       Welfare Records
                              │
                              ▼
                       AI Risk Analysis
                       ┌──────┴──────┐
                       ▼             ▼
                  Risk Signal    Data Trust
                       │             │
                       └──────┬──────┘
                              ▼
                      Historical Context
                              │
                              ▼
                         Human Review
                              │
                              ▼
                       Follow-Up / Support
```

### What Makes the Solution Different?

```text
DATA
  ↓
MODEL SIGNAL
  ↓
DATA TRUST
  ↓
HISTORICAL CONTEXT
  ↓
WHAT CHANGED
  ↓
RISK + TRUST FUSION
  ↓
HUMAN REVIEW
```

The platform does not treat a single model prediction as a standalone conclusion. It adds contextual information so authorized welfare personnel can review the signal in a broader longitudinal context.

---

# ✨ Key Features

## 👤 Personnel Welfare Workspace

- Voluntary welfare check-ins
- Weekly record submission
- AI welfare analysis
- Low / Moderate / High welfare-risk signal
- Historical assessment timeline
- Personal trajectory view
- **What Changed** insights
- Data-trust indication
- Welfare recommendations
- Privacy and ethics information

## 🧑‍💼 Welfare Officer Command Workspace

- Personnel welfare overview
- Latest assessment signals
- Historical assessment inspection
- Risk + trust context
- Trajectory analysis
- **What Changed** information
- Cases requiring human review
- Intervention desk
- Intervention history
- Structured follow-up workflow

---

# 🤖 AI-Powered Welfare Signal

The current prototype uses a **calibrated LightGBM multiclass classifier**.

The model expects:

| Property | Current Value |
|---|---|
| Model | Calibrated LightGBM |
| Feature Count | **44 numerical features** |
| Model Version | `0.2.0-sih-final` |
| Feature Version | `1.1.0` |
| Feature Contract | `artifacts/model_metadata.json` |

The exact feature order is controlled by:

```text
artifacts/model_metadata.json
```

This makes the model input contract explicit and prevents frontend-generated feature vectors from becoming an alternate source of truth.

---

# 🧠 AI Inference Pipeline

```text
Raw Weekly Records
        │
        ▼
POST /api/predict
        │
        ▼
Canonical Feature Engineering
        │
        ▼
44 Ordered Numerical Features
        │
        ▼
Preprocessing Adapter
        │
        ▼
Calibrated LightGBM
        │
        ├──────────────────┐
        ▼                  ▼
Class Probabilities   Feature Contributions
        │                  │
        └─────────┬────────┘
                  ▼
         Welfare-Risk Signal
                  │
          ┌───────┼───────┐
          ▼       ▼       ▼
         LOW   MODERATE   HIGH
```

### Backend-Authoritative Inference

The frontend **does not execute the model**.

Instead:

1. The frontend sends raw weekly records.
2. The backend validates the request.
3. Canonical feature engineering runs server-side.
4. The backend constructs the exact 44-feature vector.
5. The preprocessing pipeline is applied.
6. The calibrated LightGBM model generates predictions.
7. Class probabilities and feature contributions are returned.
8. The platform enriches the model signal with trust and historical context.

> **Pre-engineered client-supplied feature vectors are rejected.**

This establishes the backend as the authoritative source of ML input construction.

---

# 📊 Risk Signal

| Signal | Interpretation |
|---|---|
| 🟢 **Low** | Lower model-indicated welfare-risk signal |
| 🟡 **Moderate** | Intermediate model-indicated welfare-risk signal |
| 🔴 **High** | Higher model-indicated welfare-risk signal |

### Important Boundary

These are **risk signals, not diagnoses**.

The model output is not intended to represent:

- A medical diagnosis
- A psychological assessment
- A disciplinary classification
- A self-harm prediction
- An autonomous welfare decision

---

# 🔍 Data Trust & Risk Fusion

A model prediction is only as useful as the information available to the system.

Manobal-AI therefore combines:

```text
             MODEL RISK
                 │
                 ▼
           Risk Signal
                 │
                 ├───────────────┐
                 │               │
                 ▼               ▼
            Data Trust     Historical Context
                 │               │
                 └───────┬───────┘
                         ▼
                Risk + Trust Fusion
                         │
                ┌────────┼────────┐
                ▼        ▼        ▼
             REVIEW   MONITOR  VERIFY DATA
```

### Decision-Support Interpretation

| Output | Purpose |
|---|---|
| `REVIEW` | The combined context warrants authorized human review |
| `MONITOR` | The available information supports continued observation |
| `VERIFY DATA` | Data quality/trust limitations should be checked before relying heavily on the signal |

> Trajectory, early warning, What Changed, data trust, fusion, and recommendations are **platform logic / heuristics**, not additional trained models.

---

# 📈 Historical Intelligence

Manobal-AI stores previous assessments so that a welfare officer can examine change over time.

```text
Assessment 1
     │
     ▼
Assessment 2
     │
     ▼
Assessment 3
     │
     ▼
Current Assessment
     │
     ▼
Trajectory
     │
     ▼
What Changed
```

This longitudinal context helps the platform surface changes rather than treating every prediction as an isolated event.

### Historical Context Enables

- Trajectory inspection
- Early-warning logic
- Change detection
- Comparison with previous assessments
- Contextual review of current signals

---

# 🧑‍💼 Human-in-the-Loop Decision Support

## The Central Principle

```text
AI = SIGNAL
HUMAN = DECISION
```

The workflow is:

```text
AI Model
   │
   ▼
Welfare Signal
   │
   ▼
Data Trust + History
   │
   ▼
Welfare Officer
   │
   ▼
Human Review
   │
   ▼
Appropriate Follow-Up
```

## 🚫 What the AI Does NOT Do

- ❌ Diagnose mental-health conditions
- ❌ Predict self-harm
- ❌ Make disciplinary decisions
- ❌ Automatically contact personnel
- ❌ Automatically initiate welfare action
- ❌ Replace welfare officers

The prototype records and supports **human review** rather than allowing the ML model to execute welfare interventions autonomously.

---

# 🧑‍💼 Intervention Desk

When human review indicates that follow-up is appropriate:

```text
Welfare Signal
      │
      ▼
Officer Review
      │
      ▼
Context Examination
      │
      ▼
Human Decision
      │
      ▼
Intervention / Follow-Up
      │
      ▼
MongoDB Record
```

The intervention layer therefore preserves a clear boundary between:

```text
MODEL OUTPUT
     ↓
HUMAN REVIEW
     ↓
HUMAN ACTION
```

---

# 🗄️ Database Architecture

Manobal-AI uses **MongoDB** through the **Motor async driver**.

```text
Personnel
   │
   ├── Welfare Records
   ├── Risk Assessments
   └── Intervention History
```

| Collection / Data | Purpose |
|---|---|
| **Personnel** | Synthetic / demo personnel profiles |
| **Welfare Records** | Weekly welfare information |
| **Risk Assessments** | Model outputs and contextual results |
| **Interventions** | Human review and follow-up records |

---

# 🧪 Synthetic Data & Validation

The current prototype is trained on **synthetic data**.

All demo personnel and organizational values are synthetic and labeled as demo data.

```text
Synthetic Records
       ↓
Model Training
       ↓
LightGBM Artifact
       ↓
Prototype Inference
       ↓
Demo Welfare Signals
```

Before operational use, appropriately authorized data would require validation for:

- Calibration
- False positives / false negatives
- Subgroup performance
- Data quality
- Model drift
- Privacy
- Security
- Governance
- Operational suitability

> **The current prototype should not be interpreted as operationally validated simply because the model pipeline runs successfully.**

---

# 🏗️ System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                         FRONTEND                            │
│                Vite + React + TypeScript                    │
│                      Port 3000                              │
└──────────────────────────────┬──────────────────────────────┘
                               │
                         REST / JSON
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                          FASTAPI                            │
│                       backend/server.py                     │
│                                                             │
│ Welfare API │ Prediction │ History │ Intervention APIs      │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│      ML INFERENCE        │       │         MONGODB          │
│                          │       │                          │
│ Feature Engineering      │       │ Personnel                │
│ Preprocessing            │       │ Assessments              │
│ LightGBM                 │       │ Interventions            │
│ Probabilities            │       │ Welfare Records          │
│ Contributions            │       │ Historical Context       │
└──────────────────────────┘       └──────────────────────────┘
```

### Architectural Boundary

```text
                 ┌─────────────────────────────┐
                 │           FRONTEND           │
                 │     Presentation Layer       │
                 └──────────────┬──────────────┘
                                │
                         REST / JSON
                                │
                                ▼
                 ┌─────────────────────────────┐
                 │           BACKEND           │
                 │      Authoritative Layer    │
                 ├─────────────────────────────┤
                 │ Validation                  │
                 │ Feature Engineering         │
                 │ ML Inference                │
                 │ Decision Support             │
                 │ History                     │
                 │ Recommendations              │
                 │ Persistence                 │
                 └──────────────┬──────────────┘
                                │
                                ▼
                         ┌─────────────┐
                         │  MongoDB    │
                         └─────────────┘
```

---

# 📦 Model Artifacts

```text
artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md
```

| Artifact | Purpose |
|---|---|
| `risk_model.pkl` | Calibrated LightGBM classifier |
| `preprocessing_pipeline.pkl` | Runtime preprocessing transformer |
| `baseline_model.pkl` | Baseline model artifact |
| `model_metadata.json` | Feature ordering, bands, versions |
| `MODEL_CARD.md` | Intended use and limitations |

### Model Artifact Contract

The runtime inference contract is defined by the combination of:

```text
Model Artifact
      +
Preprocessing Pipeline
      +
Model Metadata
      +
Canonical Feature Engineering
```

All four should remain version-compatible.

---

# 🧩 Repository Structure

```text
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
│   ├── lib/
│   ├── tests/
│   ├── requirements.txt
│   └── .env
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── yarn.lock
│
├── tests/
│
└── memory/
    └── SPEC.md
```

---

# 🔌 API

Local backend:

```text
http://localhost:8001
```

## Core Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/predict` | Analyze raw weekly welfare records and generate the welfare signal |
| `POST` | `/api/demo/seed` | Seed synthetic demo data |
| `GET` | `/api/demo/personnel` | Retrieve demo personnel |
| `GET` | `/api/model-info` | Expose model metadata |
| `GET` | Personnel / Welfare routes | Retrieve personnel and welfare context |
| `GET` | History routes | Retrieve historical assessments |
| `POST` | Intervention routes | Record human-led follow-up |

> The prediction endpoint accepts **raw weekly records** and performs canonical feature engineering server-side.

---

# 🛠️ Technology Stack

## Backend

| Technology | Purpose |
|---|---|
| **Python** | Backend + ML ecosystem |
| **FastAPI** | REST API |
| **Motor** | Async MongoDB driver |
| **MongoDB** | Persistent data |
| **LightGBM** | Multiclass welfare classifier |
| **scikit-learn** | Preprocessing / calibration |
| **joblib** | Serialized model artifacts |
| **pytest** | Backend testing |

## Frontend

| Technology | Purpose |
|---|---|
| **Vite** | Frontend tooling |
| **React** | User interface |
| **TypeScript** | Type safety |

## Machine Learning & Decision Support

| Component | Purpose |
|---|---|
| **LightGBM** | Welfare-risk classification |
| **Preprocessing Pipeline** | Feature transformation |
| **Calibration** | Probability calibration |
| **Feature Contributions** | Model interpretation |
| **Historical Heuristics** | Trajectory / What Changed |
| **Rule Logic** | Welfare recommendations |

---

# 🔐 Security & Privacy

Welfare-related information can be highly sensitive.

The production architecture should include:

### Identity & Access

- Real authentication
- Role-based access control
- Secure sessions
- Authorized personnel boundaries

### Transport & Infrastructure

- HTTPS
- Secure database credentials
- Secrets management
- Restricted CORS
- Rate limiting

### Governance & Data Protection

- Audit logging
- Data minimization
- Retention policies
- Model governance
- Privacy review
- Security review

### Current Prototype Boundary

> The current repository is a **prototype** and does not implement production authentication or RBAC.

The prototype should therefore be treated as a demonstration of the technical workflow rather than a deployment-ready welfare-management system.

---

# 🚀 Getting Started

## Prerequisites

Install:

- Python 3
- `pip`
- Node.js
- Yarn
- MongoDB
- Git

---

## 1. Clone the Repository

```bash
git clone <repository-url>
cd ProtoMano
```

---

## 2. Configure the Backend

```bash
cd backend
pip install -r requirements.txt
```

Create:

```text
backend/.env
```

Example:

```env
MONGO_URL=mongodb://localhost:27017
DB_NAME=manobal_ai
```

---

## 3. Start the Backend

```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

Backend:

```text
http://localhost:8001
```

---

## 4. Start the Frontend

From the repository root:

```bash
cd frontend
yarn install
yarn dev
```

Frontend:

```text
http://localhost:3000
```

The Vite development server proxies:

```text
/api
```

to the FastAPI backend.

---

# 🧪 Testing

Start the backend first, then from `backend/`:

```bash
pytest
```

For serial execution:

```bash
pytest -n 0
```

The backend tests cover areas including:

- Welfare prediction
- Demo seeding
- Interventions
- Reliability-oriented behavior

---

# 🔄 End-to-End Workflow

```text
                    PERSONNEL
                        │
                        ▼
                Voluntary Check-In
                        │
                        ▼
                 Weekly Records
                        │
                        ▼
                 Manobal-AI API
                        │
                        ▼
              Feature Engineering
                        │
                        ▼
                   ML Model
                        │
                        ▼
                Welfare Signal
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
         Data Trust             History
             │                     │
             └──────────┬──────────┘
                        ▼
                Risk + Trust Fusion
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
          REVIEW     MONITOR    VERIFY DATA
             │
             ▼
        WELFARE OFFICER
             │
             ▼
         Human Review
             │
             ▼
        Intervention Desk
             │
             ▼
       Follow-Up Record
```

---

# 🗺️ Roadmap

## Phase 1 — Core Prototype

- [x] FastAPI backend
- [x] React frontend
- [x] MongoDB integration
- [x] Model artifact loading
- [x] Welfare prediction API
- [x] Personnel workflow
- [x] Officer workspace
- [x] Demo data seeding
- [x] Intervention recording

## Phase 2 — AI Decision Support

- [x] LightGBM integration
- [x] 44-feature pipeline
- [x] Calibrated probabilities
- [x] Feature contributions
- [x] Data-trust heuristic
- [x] Risk + trust fusion
- [x] Historical trajectory
- [x] What Changed
- [x] Early-warning logic
- [x] Welfare recommendations

## Phase 3 — Validation

- [ ] Authorized real-world dataset validation
- [ ] Calibration evaluation
- [ ] False-positive / false-negative analysis
- [ ] Subgroup performance analysis
- [ ] Data-quality monitoring
- [ ] Model drift detection
- [ ] Model version tracking
- [ ] Formal privacy review

## Phase 4 — Production Readiness

- [ ] Production authentication
- [ ] RBAC
- [ ] Secure sessions
- [ ] HTTPS
- [ ] Secrets management
- [ ] Audit logging
- [ ] Monitoring
- [ ] Secure deployment
- [ ] Governance framework

## Phase 5 — Advanced Intelligence

- [ ] Larger authorized datasets
- [ ] Longitudinal modeling
- [ ] Improved explainability
- [ ] Human feedback loops
- [ ] Privacy-preserving analytics
- [ ] Advanced anomaly detection
- [ ] Model drift monitoring

---

# 🧱 Design Principles

### 1. AI is Decision Support

The model produces signals; it does not make autonomous welfare decisions.

### 2. Human-in-the-Loop

Authorized human officers remain responsible for interpreting signals and determining appropriate follow-up.

### 3. Backend is the Source of Truth

Feature engineering and inference are performed server-side.

### 4. Data Trust Matters

Risk signals should be considered alongside data quality and trust.

### 5. Historical Context Matters

The platform considers trends and changes over time.

### 6. Explainability Matters

Feature contributions and contextual changes can help officers understand the signal.

### 7. Privacy by Design

Sensitive welfare information should be minimized, protected, and accessed through appropriate authorization.

### 8. Synthetic Data During Prototyping

The current model and demo use synthetic data.

### 9. No Diagnosis

A welfare-risk signal is not a medical or psychological diagnosis.

### 10. No Automated Intervention

The platform supports human-led follow-up rather than executing autonomous action.

---

# 📊 Current Project Status

**Status: Active SIH 2026 Prototype**

| Capability | Status |
|---|:---:|
| Frontend | ✅ |
| FastAPI Backend | ✅ |
| MongoDB Integration | ✅ |
| ML Artifact Loading | ✅ |
| LightGBM Inference | ✅ |
| 44-Feature Pipeline | ✅ |
| Risk Signal | ✅ |
| Class Probabilities | ✅ |
| Feature Contributions | ✅ |
| Data Trust | ✅ |
| Risk + Trust Fusion | ✅ |
| Historical Trajectory | ✅ |
| What Changed | ✅ |
| Welfare Recommendations | ✅ |
| Demo Data Seeding | ✅ |
| Officer Workspace | ✅ |
| Intervention Recording | ✅ |
| Production Authentication | ⏸️ Planned |
| Real-World Validation | ⏸️ Required |
| Production Deployment | ⏸️ Future |

---

# 👥 User Roles at a Glance

```text
┌──────────────────────────────────────────────────────────────┐
│                         MANOBAL-AI                           │
├──────────────────────────────┬───────────────────────────────┤
│          PERSONNEL           │        WELFARE OFFICER         │
├──────────────────────────────┼───────────────────────────────┤
│ Voluntary Check-In           │ Officer Workspace              │
│ Submit Weekly Records        │ Review Welfare Signals         │
│ Run AI Analysis              │ Inspect History                │
│ View Risk Signal             │ Review Data Trust              │
│ View Trajectory              │ Review What Changed            │
│ View Recommendations         │ Record Intervention             │
│ Privacy / Ethics             │ Follow-Up Workflow              │
└──────────────────────────────┴───────────────────────────────┘
```

### Role Boundary

The prototype uses a role-oriented interface to demonstrate the intended workflow. Production deployment would require formal authentication, authorization, and RBAC.

---

# 🌐 Future Scalability

The prototype can evolve toward a more modular production architecture:

```text
                         API Gateway
                              │
               ┌──────────────┼──────────────┐
               │              │              │
               ▼              ▼              ▼
        Authentication    Welfare API    Officer API
               │              │              │
               └──────────────┼──────────────┘
                              ▼
                    Decision-Support Layer
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
          ML Models       History         Data Trust
              │               │               │
              └───────────────┼───────────────┘
                              ▼
                           MongoDB
```

### Potential Future Infrastructure

```text
Redis
Background Jobs
Model Serving
Observability
Audit Logging
Data Quality Monitoring
Model Drift Monitoring
Secure Cloud Deployment
```

These components represent a future scalability direction rather than capabilities claimed for the current prototype.

---

# 🛡️ Responsible AI

Manobal-AI is designed around multiple evaluation and governance dimensions:

```text
Predictive Performance
        +
Calibration
        +
False Positives / False Negatives
        +
Data Quality
        +
Subgroup Evaluation
        +
Privacy
        +
Security
        +
Human Oversight
        +
Operational Safety
```

The current model uses **synthetic data** and is **not validated for operational deployment**.

A future operational system would require appropriate governance, validation, authorization, security controls, and privacy review before use with real personnel data.

---

# 🌱 Vision

Manobal-AI aims to make personnel welfare support more:

**Proactive. Human-Centered. Explainable. Privacy-Aware. Data-Informed.**

The long-term vision is not to replace welfare officers with AI.

It is to provide them with:

- Better information
- Better context
- Better visibility into meaningful changes
- Structured decision-support
- Earlier opportunities for human-led welfare support

```text
              NOTICE EARLIER
                    ↓
             UNDERSTAND BETTER
                    ↓
              REVIEW HUMANLY
                    ↓
                  SUPPORT
```

---

# 🏆 Smart India Hackathon 2026

**Manobal-AI** is developed as a **Smart India Hackathon 2026 prototype** addressing **Problem Statement 26186**.

The project demonstrates how machine learning, structured welfare data, historical context, and human oversight can be combined into a welfare decision-support workflow while keeping the human reviewer at the center of the process.

---

<div align="center">

## 🧠 Manobal-AI

### Turning Welfare Signals into Human-Centered Support

**AI should assist. Humans should decide.**

❤️ Built for Smart India Hackathon 2026

</div>
