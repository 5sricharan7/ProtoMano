<div align="center">

# 🧠 Manobal-AI

### AI-Assisted Personnel Welfare Intelligence & Human-in-the-Loop Decision Support Platform

**Smart India Hackathon 2026 • Problem Statement 26186**

> **AI should assist. Humans should decide.**

<p>
  A privacy-aware, welfare-first platform that transforms voluntary welfare information
  into contextual AI-assisted signals for authorized human review.
</p>

</div>

---

## 📚 Documentation

- [📘 System Architecture](architecture.md)
- [⚙️ Backend Architecture](backend-architecture.md)
- [🏠 Project README](README.md)

---

## 🧭 Contents

- [Project Overview](#-project-overview)
- [Executive Synopsis](#-executive-synopsis)
- [Problem Statement](#-problem-statement)
- [Our Solution](#-our-solution--manobal-ai)
- [Vision, Mission & Objectives](#-vision)
- [Target Users](#-target-users)
- [Key Features](#-key-features)
- [System Workflow](#-complete-system-workflow)
- [AI/ML Architecture](#-aiml-overview)
- [Decision Support](#-human-in-the-loop)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Security & Responsible AI](#-security--privacy)
- [Prototype Scope](#-prototype-scope--limitations)
- [Setup & Testing](#-installation--setup)
- [Implementation Status](#-implementation-status)
- [Production Roadmap](#-production-roadmap)
- [Future Scalability](#-future-scalability)
- [SDG & SIH Context](#-sdg-alignment)
- [Design Principles](#-design-principles)
- [Why Manobal-AI](#-why-manobal-ai)
- [Project Summary](#-project-summary)
- [Final Product Flow](#-complete-product-flow-at-a-glance)

---

## 🚀 Platform at a Glance

| Area | Current Implementation |
|---|---|
| **Frontend** | React + TypeScript + Vite |
| **Backend** | FastAPI + Python |
| **Database** | MongoDB + Motor |
| **ML Model** | Calibrated LightGBM multiclass classifier |
| **ML Input** | 44 canonical numeric features |
| **Model Version** | `0.2.0-sih-final` |
| **Feature Version** | `1.1.0` |
| **Decision Support** | Risk + Data Trust + Historical Context |
| **Explainability** | Class probabilities + feature contributions when available |
| **Human Oversight** | Welfare officer review before follow-up |
| **Demo Data** | Synthetic |
| **Current Stage** | SIH 2026 prototype |
| **Operational Deployment** | Requires authorized validation, security, governance and formal evaluation |

### Core Architecture

```text
Voluntary Welfare Data
        ↓
Canonical Feature Engineering
        ↓
44-Feature ML Contract
        ↓
Calibrated LightGBM
        ↓
Risk Signal + Probabilities
        ↓
Data Trust + Historical Context
        ↓
Risk + Trust Fusion
        ↓
Welfare Recommendations
        ↓
Authorized Human Review
        ↓
Follow-Up / Intervention Record
```

> **Architectural boundary:** the platform surfaces signals and context; it does not autonomously diagnose, discipline, contact, or intervene.

---

🌐 Project Overview
Manobal-AI is an AI-assisted personnel welfare intelligence platform
designed for uniformed-force environments where personnel may experience
demanding workloads, irregular schedules, prolonged deployments,
separation from family, and other operational pressures.

The platform is designed to support early identification of
welfare-related signals through voluntary check-ins and structured
data, while keeping a human welfare officer responsible for
interpretation and follow-up.

Manobal-AI does not attempt to replace welfare professionals or make
autonomous decisions about personnel.

Instead, it provides a structured workflow:

Voluntary Welfare Data
        ↓
Canonical Feature Engineering
        ↓
AI Risk Signal
        ↓
Data Trust Evaluation
        ↓
Historical Context
        ↓
Risk + Trust Fusion
        ↓
Welfare Recommendations
        ↓
Human Welfare Officer Review
        ↓
Appropriate Follow-up
The central philosophy is:

AI should assist. Humans should decide.

🧠 Executive Synopsis
Uniformed personnel frequently work under physically demanding,
psychologically stressful, and operationally complex conditions.
Extended deployments, irregular working hours, workload pressure,
separation from family, and exposure to difficult situations can affect
overall welfare.

Traditional welfare monitoring may depend heavily on:

manual observation

self-reporting

periodic interaction

fragmented records

delayed identification of changing patterns

This creates an opportunity for a technology-assisted welfare system
that can organize available signals and help authorized welfare officers
identify cases that may deserve attention.

Manobal-AI addresses this opportunity through a human-in-the-loop
architecture.

The system collects or receives structured welfare-related records,
transforms raw records into a canonical feature representation, runs a
calibrated LightGBM multiclass model, evaluates the trustworthiness of
the available data, compares current information with historical
assessments, and presents a contextual welfare signal to an officer.

The platform then supports human review and records
follow-up/intervention information.

The system deliberately avoids:

medical diagnosis

autonomous disciplinary action

autonomous welfare intervention

automated messaging

self-harm prediction

replacing a welfare professional

The current implementation is an SIH prototype using synthetic
demonstration data. Any operational deployment would require
authorized real-data validation, appropriate security controls,
authentication/RBAC, governance, and formal evaluation.

🚨 Problem Statement
AI-Based Predictive Personnel Stress and Welfare Monitoring System for Uniformed Forces
The project addresses the challenge of identifying early indicators of
personnel welfare concerns in uniformed-force environments using a
technology-assisted and human-centered approach.

Operational environments can create conditions in which changes in
welfare may not always be immediately visible through conventional
observation.

A digital platform can help organize available information and surface
patterns for welfare officers, provided that:

data is handled responsibly,

AI output is treated as a signal rather than a diagnosis,

false positives and false negatives are considered,

explanations and data trust are surfaced,

personnel welfare and confidentiality remain central,

human review remains mandatory before follow-up action.

🔎 Problem Analysis
Existing Challenges
1. Manual Identification
Welfare concerns may depend on manual observation and periodic
interaction.

2. Delayed Recognition
Changes can accumulate over time before becoming obvious to supervisors
or welfare staff.

3. Fragmented Information
Relevant signals may exist across multiple categories of records.

4. Lack of Historical Context
A single observation may not show whether a person's situation is
stable, improving, or changing.

5. Data Quality Uncertainty
An AI signal is less useful when the underlying data is incomplete,
inconsistent, or unreliable.

6. Risk of Stigmatization
A welfare system must avoid turning a support mechanism into a
disciplinary or labeling mechanism.

7. Need for Human Judgment
Automated predictions cannot replace contextual understanding by an
authorized welfare professional.

💡 Our Solution --- Manobal-AI
Manobal-AI introduces a human-in-the-loop welfare intelligence
layer.

The platform combines:

Structured Welfare Records
          +
Machine Learning
          +
Data Trust
          +
Historical Intelligence
          +
Explainability
          +
Human Review
Instead of presenting only a model prediction, the platform provides a
broader decision-support context.

Core output
The system produces welfare-risk signals such as:

LOW
MODERATE
HIGH
These represent AI-assisted welfare signals, not medical diagnoses.

🎯 Vision
To build a responsible digital welfare-support ecosystem in which AI
helps authorized personnel identify meaningful changes earlier while
preserving confidentiality, dignity, human judgment, and the autonomy of
the people being supported.

🎯 Mission
Manobal-AI aims to:

organize welfare-related information,

identify potentially meaningful patterns,

provide contextual AI-assisted signals,

improve historical visibility,

surface data-quality concerns,

support welfare officers,

record human-reviewed follow-up,

maintain responsible AI boundaries.

🎯 Objectives
Primary Objectives
Develop an AI-assisted welfare monitoring workflow.

Generate interpretable welfare-risk signals.

Maintain a human-in-the-loop review process.

Use historical assessments to provide context.

Evaluate data trust before over-interpreting model output.

Keep model inference server-side.

Maintain a clear separation between AI signals and human decisions.

Secondary Objectives
Provide a structured welfare dashboard.

Support voluntary personnel check-ins.

Maintain intervention records.

Create an architecture that can later be validated using authorized
real data.

Provide a production-scalable technical foundation.

👥 Target Users
Personnel
Personnel can participate through voluntary welfare check-ins and
provide structured information relevant to their current situation.

Welfare Officers
Authorized welfare officers can:

view personnel profiles,

review historical information,

run AI-assisted analysis,

inspect risk and trust information,

review changes,

consider recommendations,

record follow-up/intervention decisions.

🔄 Core Use Case
Personnel
   │
   │ Voluntary Check-in
   ▼
Structured Welfare Data
   │
   ▼
Manobal-AI Backend
   │
   ├── Feature Engineering
   ├── ML Inference
   ├── Data Trust
   ├── Historical Analysis
   └── Recommendations
   │
   ▼
Welfare Officer
   │
   ▼
Human Review
   │
   ▼
Appropriate Welfare Follow-up
⭐ Key Features
1. Voluntary Welfare Check-ins
Structured welfare information can be provided through the platform.

2. AI-Assisted Welfare Signal
The backend generates a calibrated multiclass welfare-risk signal.

3. Probability-Based Output
The system can expose class probabilities instead of hiding model
uncertainty behind a single label.

4. Feature Contributions
LightGBM feature contributions can be surfaced when available to help
explain influential signals.

5. Data Trust
The platform evaluates whether the available data should be treated
confidently or verified before interpretation.

6. Risk + Trust Fusion
Risk output and data trust are combined into contextual states such as:

REVIEW_RECOMMENDED
MONITOR
VERIFY_DATA
7. Historical Intelligence
Previous assessments provide longitudinal context.

8. Trajectory
The platform can identify changes in assessment patterns over time.

9. "What Changed"
The system highlights meaningful changes between historical context and
current observations.

10. Welfare Recommendations
Rule-based recommendations help officers consider appropriate
welfare-oriented follow-up.

11. Intervention Records
Human-reviewed follow-up can be recorded in MongoDB.

12. Demo Mode
Synthetic personnel and historical assessments can be generated for
demonstration.

13. Ethical AI Boundary
The system is explicitly designed not to diagnose, discipline, or
autonomously intervene.

🔁 Complete System Workflow
                    ┌──────────────────────┐
                    │      Personnel       │
                    │   Voluntary Input    │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   React Frontend     │
                    └──────────┬───────────┘
                               │
                         REST / JSON
                               │
                               ▼
                    ┌──────────────────────┐
                    │    FastAPI Backend   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Request Validation   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Feature Engineering  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ 44 Canonical Features│
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Preprocessing        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Calibrated LightGBM  │
                    └──────────┬───────────┘
                               │
                  ┌────────────┴─────────────┐
                  ▼                          ▼
          Risk Probabilities       Feature Contributions
                  │                          │
                  └────────────┬─────────────┘
                               ▼
                    ┌──────────────────────┐
                    │ Data Trust Evaluation │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Historical Context   │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Risk + Trust Fusion  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Recommendations      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Welfare Officer      │
                    │ Human Review         │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Intervention Record  │
                    └──────────┬───────────┘
                               │
                               ▼
                            MongoDB
👤 Personnel Experience
The personnel-facing side is designed around a voluntary and
welfare-oriented interaction model.

A typical flow is:

Open Platform
      ↓
Personnel Area
      ↓
Welfare Check-in
      ↓
Submit Structured Information
      ↓
Data Stored Securely
      ↓
Available for Authorized Welfare Workflow
The current SIH prototype should not be interpreted as a production
identity-management system.

🧑‍💼 Welfare Officer Experience
The officer workflow is the primary decision-support workflow.

Officer Dashboard
      ↓
Personnel List
      ↓
Select Personnel
      ↓
View Profile + History
      ↓
Run AI Analysis
      ↓
Review:
  • Risk Signal
  • Probabilities
  • Data Trust
  • Historical Trajectory
  • What Changed
  • Recommendations
      ↓
Human Review
      ↓
Monitor / Follow-up / Intervention
      ↓
Record Review
🤖 AI/ML Overview
The current ML component uses a calibrated LightGBM multiclass
classifier.

The model expects:

44 numeric features
The inference architecture is:

Raw Weekly Records
       ↓
Canonical Feature Engineering
       ↓
44 Numeric Features
       ↓
Preprocessing Pipeline
       ↓
Calibrated LightGBM
       ↓
Class Probabilities
       ↓
Feature Contributions
The model itself is only one component of the larger decision-support
system.

🧪 AI Inference Pipeline
Step 1 --- Raw Input
The frontend submits raw weekly records.

Step 2 --- Validation
The backend validates the incoming request.

Step 3 --- Feature Engineering
The backend converts raw records into the canonical feature
representation.

Step 4 --- Feature Contract
The resulting vector must match the expected 44-feature model contract.

Step 5 --- Preprocessing
The serialized preprocessing pipeline transforms the model input.

Step 6 --- Model Inference
The calibrated LightGBM classifier generates multiclass probabilities.

Step 7 --- Explainability
Feature contributions are generated when supported by the model.

Step 8 --- Context
Historical assessments and data trust are incorporated.

Step 9 --- Fusion
Risk and trust are combined into a decision-support state.

Step 10 --- Recommendations
Rule-based welfare recommendations are generated.

Step 11 --- Human Review
The officer interprets the complete result and decides the appropriate
follow-up.

🔢 44-Feature Architecture
The current model expects 44 numeric features in a specific order.

The feature contract is associated with:

artifacts/model_metadata.json
The feature version is:

1.1.0
The backend owns the feature-engineering process.

RAW DATA
   ↓
Canonical Feature Engineering
   ↓
Feature Names
   ↓
Feature Ordering
   ↓
44 Numeric Features
   ↓
Preprocessing
   ↓
LightGBM
Why server-side feature engineering?
It provides:

one canonical implementation,

consistent training/inference behavior,

reduced client-side manipulation,

easier model versioning,

better control over the ML input contract.

📊 Risk Signal
Manobal-AI produces a welfare-risk signal based on the trained model.

The signal can be represented as:

LOW
MODERATE
HIGH
The output should be interpreted as:

An AI-assisted welfare signal that may justify human review.

It should not be interpreted as:

a medical diagnosis,

a psychological diagnosis,

proof of a condition,

a disciplinary classification,

an autonomous decision.

🛡️ Data Trust
The platform recognizes that prediction quality depends not only on the
model but also on the quality and completeness of the available data.

A separate data-trust heuristic helps contextualize the AI signal.

Conceptually:

Input Quality
     +
Completeness / Consistency
     +
Context
     ↓
Data Trust
This allows the platform to distinguish between:

Strong signal
and

Signal requiring data verification
⚖️ Risk + Trust Fusion
The platform combines:

ML Risk
   +
Data Trust
   +
Historical Context
to produce decision-support states.

Example states:

State Meaning

REVIEW_RECOMMENDED Signal may deserve human welfare
review

MONITOR Continue observation/contextual
monitoring

These are platform decision-support states, not additional trained
models.

📈 Historical Intelligence
A welfare assessment should not necessarily be interpreted as an
isolated event.

Manobal-AI maintains historical assessment context.

Assessment 1
      ↓
Assessment 2
      ↓
Assessment 3
      ↓
Current Assessment
      ↓
Historical Intelligence
This enables:

longitudinal comparison,

trajectory analysis,

recent-change detection,

historical context for officer review.

🔄 Trajectory Analysis
The platform can use historical assessments to provide a trajectory
view.

Conceptually:

Historical Assessments
        ↓
Temporal Comparison
        ↓
Trend / Trajectory
        ↓
Current Context
The trajectory is platform logic and should not be confused with another
trained predictive model.

🔍 "What Changed"
One of the important contextual features is the ability to communicate
meaningful changes.

Historical State
       +
Current State
       ↓
Comparison
       ↓
Meaningful Changes
       ↓
"What Changed"
This helps an officer understand why the current assessment deserves
attention, rather than showing only a numerical prediction.

💬 Welfare Recommendations
The recommendation layer uses rule-based platform logic.

Risk Signal
     +
Data Trust
     +
Historical Context
     +
Observed Changes
     ↓
Welfare Recommendations
Recommendations are intended to support welfare officers in considering
appropriate next steps.

They do not autonomously execute interventions.

🔎 Explainability
Manobal-AI is designed to expose more information than a simple:

HIGH RISK
screen.

The system can provide:

calibrated probabilities,

feature contributions when available,

data trust,

historical trajectory,

"What Changed",

recommendation context.

This supports a more transparent human review workflow.

👨‍⚖️ Human-in-the-Loop
Human oversight is a fundamental architectural requirement.

AI Model
   ↓
Risk Signal
   ↓
Contextual Analysis
   ↓
Welfare Officer
   ↓
Human Judgment
   ↓
Follow-up Decision
The model does not independently:

contact personnel,

issue disciplinary action,

diagnose conditions,

initiate welfare intervention,

make operational decisions.

📝 Intervention Desk
The intervention workflow records human-reviewed follow-up.

AI Assessment
      ↓
Officer Review
      ↓
Follow-up Decision
      ↓
Intervention Record
      ↓
MongoDB
This creates a separation between:

AI OUTPUT
and

HUMAN DECISION
which is essential for responsible welfare-oriented deployment.

🏗️ System Architecture
┌──────────────────────────────────────────────────────────────┐
│                       MANOBAL-AI                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  PERSONNEL / WELFARE OFFICER                                 │
│              │                                               │
│              ▼                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              React + TypeScript Frontend               │  │
│  │                                                        │  │
│  │ Dashboard | Personnel | Analysis | Insights | Ethics   │  │
│  └──────────────────────────┬─────────────────────────────┘  │
│                             │                                │
│                          /api                                │
│                             │                                │
│  ┌──────────────────────────▼─────────────────────────────┐  │
│  │                    FastAPI Backend                     │  │
│  │                                                        │  │
│  │ API | Validation | Services | Feature Engineering      │  │
│  └───────────────┬──────────────────────┬─────────────────┘  │
│                  │                      │                    │
│                  ▼                      ▼                    │
│       ┌───────────────────┐    ┌────────────────────────┐  │
│       │  ML / Decision    │    │       MongoDB           │  │
│       │     Support       │    │ Personnel | Assessments │  │
│       │                   │    │ Interventions | Demo    │  │
│       └─────────┬─────────┘    └────────────────────────┘  │
│                 │                                            │
│                 ▼                                            │
│       ┌──────────────────────┐                               │
│       │ ML Artifacts         │                               │
│       │ LightGBM + Pipeline  │                               │
│       └──────────────────────┘                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
⚙️ Backend Architecture
The backend uses:

FastAPI
Python
Motor
MongoDB
Pydantic
Uvicorn
Pytest
Logical layers:

API
 ↓
Validation
 ↓
Feature Engineering
 ↓
ML Inference
 ↓
Decision Support
 ↓
Persistence
The backend is documented separately in:

Manobal-AI-BACKEND-ARCHITECTURE.md
🖥️ Frontend Architecture
The frontend uses:

Vite
React
TypeScript
Development server:

http://localhost:3000
The frontend communicates with the backend through relative:

/api/...
requests.

Vite proxies these API requests to the FastAPI server.

Main application areas
/
├── Landing
│
├── /login
│   └── Demo role selection
│
├── /officer
│   └── Officer command/dashboard
│
├── /personnel
│   └── Personnel listing
│
├── /personnel/:id
│   └── Personnel profile + analysis
│
├── /analysis
│   └── Analysis workspace
│
├── /insights
│   └── Insights
│
├── /interventions
│   └── Human-reviewed follow-up
│
└── /ethics
    └── Responsible-AI information
🗄️ Database Architecture
MongoDB is used through the Motor driver.

Logical data areas include:

MongoDB
│
├── Personnel
│
├── Assessments
│
├── Interventions
│
└── Demo / Welfare Records
The database supports the longitudinal nature of the application.

Personnel
   │
   ├── Profile
   ├── Current Assessment
   ├── Historical Assessments
   └── Intervention History
🔌 API Architecture
The backend exposes APIs under:

/api
Prediction
POST /api/predict
Used to:

accept raw weekly records,

derive canonical features,

execute ML inference,

return probabilities and contextual decision-support output.

Demo Seed
POST /api/demo/seed
Used to:

create synthetic demonstration personnel,

generate historical assessments,

run the actual uploaded model,

populate demo data.

Demo Personnel
GET /api/demo/personnel
Used to retrieve synthetic personnel profiles and historical context.

Interventions
/api/interventions
Used to record human-reviewed welfare follow-up information.

📦 ML Artifact Architecture
The current model artifacts are stored under:

artifacts/
│
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md
Model Metadata
Model Version:
0.2.0-sih-final

Feature Version:
1.1.0

Input:
44 numeric features

Model:
Calibrated LightGBM multiclass classifier
The artifact directory can be configured using:

MODEL_ARTIFACT_DIR
📁 Repository Structure
Manobal-AI/
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
│   └── requirements.txt
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
🛠️ Technology Stack
Category Technology

Frontend React
Language TypeScript
Build Tool Vite
Backend FastAPI
Backend Language Python
Database MongoDB
Database Driver Motor
ML LightGBM
Model Type Calibrated Multiclass Classifier
Validation Pydantic
API REST / JSON
Server Uvicorn
Testing Pytest
Environment .env configuration

🔐 Security & Privacy
Manobal-AI is designed with privacy and confidentiality as important
architectural principles.

Current Prototype Boundary
The browser should not directly access:

MongoDB credentials,

model artifacts,

preprocessing artifacts,

internal feature-engineering implementation.

These remain behind the FastAPI backend.

Production Requirements
Before operational deployment, the system would require stronger
controls such as:

production authentication,

role-based access control,

secure secret management,

encryption in transit,

appropriate encryption at rest,

audit logging,

access monitoring,

retention policies,

data minimization,

authorized data governance,

formal security assessment.

🤝 Responsible AI
Responsible AI is central to the project rather than an additional
feature.

Manobal-AI is NOT:
❌ A medical diagnosis system
❌ A disciplinary system
❌ An autonomous surveillance system
❌ A self-harm prediction system
❌ An automated intervention engine
❌ An autonomous operational decision-maker
Manobal-AI IS:
✅ A welfare-oriented decision-support system
✅ A human-in-the-loop AI platform
✅ A contextual risk-signal system
✅ A historical intelligence layer
✅ A data-trust-aware workflow
✅ A tool for authorized welfare officers
🧭 Ethical Decision Boundary
             AI
              │
              ▼
       Detect / Surface
          a Signal
              │
              ▼
        Provide Context
              │
              ▼
       Human Officer
              │
              ▼
        Human Review
              │
              ▼
      Appropriate Action
The system deliberately stops autonomous decision-making at the
human-review boundary.

⚠️ Prototype Scope & Limitations
The current project is an SIH prototype.

1. Synthetic Data
The demonstration workflow uses synthetic data.

2. No Production Authentication
The current demo uses a browser role switch rather than production-grade
authentication and RBAC.

3. Model Validation
The model has been trained using synthetic data and requires authorized
real-data revalidation before operational use.

4. Human Review
A welfare officer must review signals before welfare action.

5. No Automated Messaging
The current system does not autonomously send welfare messages.

6. No Diagnosis
The system does not diagnose medical or psychological conditions.

7. No Discipline
AI output is not used to automatically initiate disciplinary action.

8. No Operational Deployment Claim
The prototype should not be interpreted as validated for operational
use.

🧪 Synthetic Data & Demo Mode
The prototype provides a controlled demo environment.

Calling:

POST /api/demo/seed
creates synthetic demonstration personnel and historical assessment
records.

The important point is that the demo uses the actual uploaded model
artifacts to demonstrate the inference pipeline.

Synthetic Demo Data
       ↓
Real Feature Engineering
       ↓
Real Preprocessing Pipeline
       ↓
Real Uploaded LightGBM Artifact
       ↓
Historical Assessments
       ↓
Demo Dashboard
This allows the complete product workflow to be demonstrated without
using operational personnel data.

🚀 Installation & Setup
Prerequisites
Python
Node.js
Yarn
MongoDB
Backend Setup
cd backend
Install dependencies:

pip install -r requirements.txt
Configure environment variables:

MONGO_URL=
DB_NAME=
CORS_ORIGINS=
MODEL_ARTIFACT_DIR=
APP_TZ=
BACKEND_URL=
Required:

MONGO_URL
DB_NAME
Start the backend:

uvicorn server:app --host 0.0.0.0 --port 8001 --reload
Frontend Setup
cd frontend
Install dependencies:

yarn install
Start the development server:

yarn dev
Open:

http://localhost:3000
🧪 Testing
The project uses Pytest.

Run:

pytest
For serial execution:

pytest -n 0
Testing is intended to validate:

API behavior,

inference workflow,

request validation,

feature engineering,

decision-support logic,

persistence behavior,

integration behavior.

🔄 End-to-End Technical Flow
┌──────────────────────┐
│ Personnel / Officer  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ React + TypeScript   │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ FastAPI REST API     │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Request Validation    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Raw Weekly Records    │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Feature Engineering  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ 44 Feature Contract  │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Preprocessing        │
└──────────┬───────────┘
           │
           ▼
┌──────────────────────┐
│ Calibrated LightGBM  │
└──────────┬───────────┘
           │
           ├───────────────┐
           ▼               ▼
      Probabilities    Contributions
           │               │
           └───────┬───────┘
                   ▼
          Data Trust Evaluation
                   │
                   ▼
          Historical Intelligence
                   │
                   ▼
           Risk + Trust Fusion
                   │
                   ▼
          Welfare Recommendations
                   │
                   ▼
           Human Officer Review
                   │
                   ▼
          Intervention / Follow-up
                   │
                   ▼
                MongoDB
📊 Implementation Status
Component Status

React + Vite frontend ✅ Implemented
FastAPI backend ✅ Implemented
MongoDB integration ✅ Implemented
Synthetic demo workflow ✅ Implemented
Server-side feature engineering ✅ Implemented
44-feature model contract ✅ Implemented
Calibrated LightGBM inference ✅ Implemented
Probability output ✅ Implemented
Feature contributions ✅ Implemented when available
Data-trust heuristic ✅ Implemented
Risk + trust fusion ✅ Implemented
Historical trajectory ✅ Implemented
"What Changed" ✅ Implemented
Rule-based recommendations ✅ Implemented
Intervention records ✅ Implemented
Production authentication/RBAC ⏳ Future
Authorized real-data validation ⏳ Future
Production security hardening ⏳ Future
Production observability ⏳ Future

🛣️ Production Roadmap
Phase 1 --- Prototype
✅ Core UI
✅ FastAPI backend
✅ MongoDB
✅ ML inference
✅ 44-feature pipeline
✅ Historical intelligence
✅ Data trust
✅ Human review
Phase 2 --- Security Hardening
Production Authentication
        ↓
RBAC
        ↓
Secure Secrets
        ↓
Audit Logging
        ↓
Access Controls
Phase 3 --- Data Validation
Authorized Data
      ↓
Data Cleaning
      ↓
Data Governance
      ↓
Longitudinal Evaluation
      ↓
Real-Data Model Validation
Phase 4 --- ML Validation
Authorized Dataset
      ↓
Person-Level Splitting
      ↓
Temporal Validation
      ↓
Calibration
      ↓
False Positive / False Negative Analysis
      ↓
Bias / Subgroup Evaluation
      ↓
Model Versioning
Phase 5 --- Production Infrastructure
Containerized Deployment
        ↓
Managed Database
        ↓
Secure API Gateway
        ↓
Observability
        ↓
Audit Infrastructure
        ↓
Controlled Production Rollout
📈 Future Scalability
Manobal-AI can evolve from an SIH prototype into a larger welfare
intelligence platform.

Potential future directions include:

Secure Identity
Enterprise Authentication
+
Role-Based Access Control
Model Governance
Model Registry
+
Versioning
+
Validation
+
Rollback
Data Governance
Data Lineage
+
Retention Policies
+
Consent / Access Controls
+
Audit Logs
Observability
API Monitoring
+
Model Monitoring
+
Data Drift Monitoring
+
System Health
Scalable Infrastructure
Load Balancer
      ↓
API Services
      ↓
Database
      +
Model Serving
      +
Monitoring
These are future architectural directions and are not claims about the
current prototype.

🌱 SDG Alignment
Manobal-AI can be positioned in relation to broader Sustainable
Development Goals through its focus on personnel welfare, responsible
technology, and institutional support.

Potentially relevant SDGs include:

SDG Relevance

SDG 3 --- Good Health and Welfare-oriented early support and
Well-Being well-being awareness

SDG 8 --- Decent Work and Worker welfare and healthier
Economic Growth working environments

SDG 9 --- Industry, Innovation Responsible application of AI and
and Infrastructure digital infrastructure

The strongest conceptual alignment is with well-being, responsible
work environments, innovation, and institutional support.

🏆 SIH Context
Manobal-AI was developed as an SIH 2026 prototype addressing the
problem of AI-assisted personnel stress and welfare monitoring for
uniformed forces.

The solution is designed around the following SIH-relevant requirements:

predictive welfare signals,

personnel welfare monitoring,

dashboard-based decision support,

structured self-assessment/check-ins,

intervention recommendations,

privacy and confidentiality,

reduced risk of stigmatization,

transparent AI,

consideration of false positives and false negatives,

secure data handling,

human-centered intervention.

The prototype intentionally demonstrates these concepts without claiming
operational validation.

🧩 Design Principles
1. Human Before Automation
AI provides support; humans retain decision authority.

2. Welfare Before Discipline
The platform is designed for welfare support rather than disciplinary
classification.

3. Context Before Conclusion
Current predictions are accompanied by history, trust, and change
information.

4. Server-Side Intelligence
Feature engineering and model inference remain inside the backend.

5. Explainability
The system provides probabilities and supporting signals where
available.

6. Data Awareness
The quality of input data is explicitly considered.

7. Modular Architecture
Frontend, backend, ML, persistence, and decision-support logic remain
separable.

8. Responsible Deployment
Synthetic-data demonstration is clearly separated from future
operational deployment.

🔬 Model vs Platform Logic
A major architectural distinction in Manobal-AI is the separation
between trained machine learning and deterministic platform logic.

Trained Components
Preprocessing Pipeline
        +
Calibrated LightGBM Model
Platform Components
Canonical Feature Engineering
Data Trust Heuristic
Historical Trajectory
"What Changed"
Risk + Trust Fusion
Welfare Recommendations
This distinction prevents the platform from presenting every feature as
a separate AI model.

🏛️ Complete Architecture
                         MANOBAL-AI
                             │
             ┌───────────────┴────────────────┐
             │                                │
        PERSONNEL                       WELFARE OFFICER
             │                                │
             └───────────────┬────────────────┘
                             ▼
                   ┌──────────────────┐
                   │ React Frontend   │
                   │ Vite + TypeScript│
                   └────────┬─────────┘
                            │
                         REST / API
                            │
                            ▼
                   ┌──────────────────┐
                   │ FastAPI Backend  │
                   └────────┬─────────┘
                            │
             ┌──────────────┼──────────────┐
             │              │              │
             ▼              ▼              ▼
       Validation      Persistence     ML Services
             │              │              │
             │              ▼              ▼
             │          MongoDB       Feature Engineering
             │                             │
             │                             ▼
             │                        44 Features
             │                             │
             │                             ▼
             │                       Preprocessing
             │                             │
             │                             ▼
             │                       LightGBM Model
             │                             │
             │                  ┌──────────┴──────────┐
             │                  ▼                     ▼
             │             Probabilities       Contributions
             │                  │                     │
             └──────────────────┴──────────┬──────────┘
                                           ▼
                                  Data Trust Layer
                                           │
                                           ▼
                                  Historical Intelligence
                                           │
                                           ▼
                                  Risk + Trust Fusion
                                           │
                                           ▼
                                  Recommendations
                                           │
                                           ▼
                                  Human Officer Review
                                           │
                                           ▼
                                  Intervention Record
                                           │
                                           ▼
                                        MongoDB
🧠 Why Manobal-AI?
The key differentiator is not simply the use of machine learning.

The platform combines:

ML Prediction
     +
Uncertainty / Probability
     +
Data Trust
     +
Historical Context
     +
Change Detection
     +
Human Review
This changes the workflow from:

"AI says HIGH"
to:

"AI detected a signal.
Here is the confidence context.
Here is the data trust.
Here is the historical trajectory.
Here is what changed.
Here are welfare-oriented considerations.
Now the human reviews the case."
That distinction is fundamental to the project's responsible-AI design.

📋 Project Summary
Category Details

Project Manobal-AI

Purpose AI-assisted personnel welfare
decision support

Domain Personnel Welfare / Uniformed
Forces

Type Human-in-the-loop decision-support
platform

Frontend React + TypeScript + Vite

Backend FastAPI + Python

Database MongoDB

ML Calibrated LightGBM multiclass
classifier

Input Raw weekly welfare records

Feature Vector 44 numeric features

Model Version 0.2.0-sih-final

Feature Version 1.1.0

Explainability Class probabilities + feature
contributions when available

Context Historical trajectory + "What
Changed"

Trust Data-trust heuristic

Decision Layer Risk + Trust Fusion

Recommendations Rule-based welfare recommendations

Human Oversight Welfare officer review

Demo Data Synthetic

Current Status SIH prototype

Production Authentication Not yet implemented

Production Real-Data Validation Required before operational use
🚀 Complete Product Flow at a Glance
┌──────────────────────────────────────────────────────────────┐
│                       MANOBAL-AI                             │
│                                                              │
│             VOLUNTARY WELFARE CHECK-IN                       │
│                         │                                    │
│                         ▼                                    │
│                 STRUCTURED DATA                              │
│                         │                                    │
│                         ▼                                    │
│              CANONICAL FEATURE ENGINEERING                   │
│                         │                                    │
│                         ▼                                    │
│                  44 FEATURE VECTOR                            │
│                         │                                    │
│                         ▼                                    │
│                CALIBRATED LIGHTGBM                           │
│                         │                                    │
│              ┌──────────┴──────────┐                         │
│              ▼                     ▼                         │
│        RISK PROBABILITY      FEATURE SIGNALS                │
│              │                     │                         │
│              └──────────┬──────────┘                         │
│                         ▼                                    │
│                    DATA TRUST                                │
│                         │                                    │
│                         ▼                                    │
│                HISTORICAL CONTEXT                            │
│                         │                                    │
│                         ▼                                    │
│                   WHAT CHANGED                               │
│                         │                                    │
│                         ▼                                    │
│                 RISK + TRUST FUSION                          │
│                         │                                    │
│                         ▼                                    │
│              WELFARE RECOMMENDATIONS                         │
│                         │                                    │
│                         ▼                                    │
│                 HUMAN OFFICER                                │
│                         │                                    │
│                         ▼                                    │
│                   HUMAN REVIEW                               │
│                         │                                    │
│                         ▼                                    │
│              FOLLOW-UP / INTERVENTION                        │
│                         │                                    │
│                         ▼                                    │
│                      MONGODB                                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
🎯 Final Synopsis
Manobal-AI is a human-centered AI-assisted welfare intelligence
platform for uniformed personnel.

Its purpose is not to automate welfare decisions.

Its purpose is to help welfare officers transform fragmented and
time-dependent welfare information into a structured decision-support
workflow.

The system combines:

voluntary welfare data,

canonical feature engineering,

a calibrated LightGBM model,

probability-based risk signals,

data-trust evaluation,

historical intelligence,

trajectory analysis,

"What Changed" analysis,

rule-based welfare recommendations,

human-reviewed intervention records.

The technical architecture keeps ML inference on the backend, stores
application history in MongoDB, and provides a React-based interface for
personnel and welfare officers.

Most importantly, the architecture establishes a clear boundary:

AI
 ↓
ASSISTS

HUMAN
 ↓
REVIEWS

WELFARE PROCESS
 ↓
DECIDES
Manobal-AI
Turning welfare data into contextual signals --- while keeping
humans in control.

📌 Project Status
Current Stage: SIH 2026 Prototype

Current Demonstration: Synthetic-data end-to-end workflow

Core AI: Calibrated LightGBM multiclass model

Architecture: React + FastAPI + MongoDB + ML Decision Support

Design Philosophy: Human-in-the-loop, privacy-oriented,
welfare-first

Production Requirement: Authorized real-data validation and
production security/governance before operational deployment.

❤️ Closing Principle
AI should assist. Humans should decide.

---

## 🔗 Related Documentation

| Document | Purpose |
|---|---|
| [`README.md`](README.md) | Product overview, features, setup and project introduction |
| [`architecture.md`](architecture.md) | Complete system-level architecture |
| [`backend-architecture.md`](backend-architecture.md) | Detailed FastAPI, ML, persistence and backend design |

---

<div align="center">

### 🧠 Manobal-AI

**Turning welfare data into contextual signals — while keeping humans in control.**

**AI should assist. Humans should decide.**

❤️ Built for Smart India Hackathon 2026

</div>
