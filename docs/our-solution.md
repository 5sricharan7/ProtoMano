🧠 Manobal-AI

AI-Powered Personnel Welfare Signal & Human-in-the-Loop Decision-Support Platform

Manobal-AI is a Smart India Hackathon 2026 prototype designed to help authorized welfare personnel identify meaningful welfare signals earlier through voluntary check-ins, structured organizational data, machine-learning analysis, historical context, and human-led follow-up.








Smart India Hackathon 2026 — Problem Statement 26186

📌 Overview

Personnel serving in CAPFs, Armed Forces, and other uniformed services can operate under demanding conditions involving extended deployments, irregular duty schedules, workload pressure, transfers, training commitments, family separation, and other operational challenges.

The SIH problem statement calls for an AI-powered personnel stress and welfare monitoring system that can identify early indicators while protecting privacy, confidentiality, dignity, and organizational trust.

Manobal-AI addresses this requirement through a human-in-the-loop welfare workflow:

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
Low / Moderate / High
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

The system is intentionally designed as decision support, not autonomous personnel decision-making.

🎯 Problem Statement

The Challenge

Welfare concerns may emerge gradually through changes in workload, leave patterns, deployment conditions, wellness responses, and other indicators.

Traditional identification can depend heavily on manual observation and self-reporting. At larger scale, this can make it difficult to consistently identify changes over time and prioritize cases that may warrant human attention.

The SIH problem statement specifically highlights indicators such as leave patterns, deployment history, duty schedules, transfer frequency, training commitments, workload trends, voluntary wellness assessments, and authorized wellness data.

The core gap

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

💡 Our Solution — Manobal-AI

Manobal-AI converts authorized and voluntarily provided welfare information into structured welfare signals and contextual insights for human review.

                MANOBAL-AI
                     │
       ┌─────────────┴─────────────┐
       │                           │
       ▼                           ▼
   PERSONNEL                WELFARE OFFICER
       │                           │
       ▼                           ▼
 Voluntary Check-In          Officer Workspace
       │                           │
       └─────────────┬─────────────┘
                     ▼
              Welfare Records
                     │
                     ▼
              AI Risk Analysis
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
      Risk Signal           Data Trust
          │                     │
          └──────────┬──────────┘
                     ▼
             Historical Context
                     │
                     ▼
              Human Review
                     │
                     ▼
             Follow-Up / Support

What makes the solution different?

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

✨ Key Features

👤 Personnel Welfare Workspace

Voluntary welfare check-ins

Weekly record submission

AI welfare analysis

Low / Moderate / High welfare-risk signal

Historical assessment timeline

Personal trajectory view

“What Changed” insights

Data-trust indication

Welfare recommendations

Privacy and ethics information

🧑‍💼 Welfare Officer Command Workspace

Personnel welfare overview

Latest assessment signals

Historical assessment inspection

Risk + trust context

Trajectory analysis

“What Changed” information

Cases requiring human review

Intervention desk

Intervention history

Structured follow-up workflow

🤖 AI-Powered Welfare Signal

The current prototype uses a calibrated LightGBM multiclass classifier.

The model expects:

44 numerical features

with their exact order defined by:

artifacts/model_metadata.json

Current metadata:

Model Version:    0.2.0-sih-final
Feature Version:  1.1.0
Feature Count:    44

🧠 AI Inference Pipeline

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
        ├───────────────┐
        ▼               ▼
Class Probabilities   Feature Contributions
        │               │
        └───────┬───────┘
                ▼
       Welfare-Risk Signal
                │
       ┌────────┼────────┐
       ▼        ▼        ▼
      LOW   MODERATE    HIGH

The frontend does not execute the model. It sends raw weekly records to the backend, where canonical feature engineering and inference are performed.

Pre-engineered client-supplied feature vectors are rejected.

📊 Risk Signal

Signal

Interpretation

🟢 Low

Lower model-indicated welfare-risk signal

🟡 Moderate

Intermediate model-indicated welfare-risk signal

🔴 High

Higher model-indicated welfare-risk signal

These are risk signals, not diagnoses.

🔍 Data Trust & Risk Fusion

A model prediction is only as useful as the information available to the system.

Manobal-AI therefore combines the model signal with a data-trust heuristic and historical context.

             MODEL RISK
                 │
                 ▼
           Risk Signal
                 │
                 +
             Data Trust
                 │
                 +
          Historical Context
                 │
                 ▼
          Risk + Trust Fusion
                 │
       ┌─────────┼─────────┐
       ▼         ▼         ▼
    REVIEW    MONITOR   VERIFY DATA

Trajectory, early warning, What Changed, data trust, fusion, and recommendations are platform logic / heuristics, not additional trained models.

📈 Historical Intelligence

Manobal-AI stores previous assessments so that a welfare officer can examine change over time.

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

This helps the system provide context rather than treating one model prediction as an isolated conclusion.

🧑‍💼 Human-in-the-Loop Decision Support

The central principle is:

AI = SIGNAL
Human = DECISION

The system follows:

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

The AI does NOT:

❌ Diagnose mental-health conditions
❌ Predict self-harm
❌ Make disciplinary decisions
❌ Automatically contact personnel
❌ Automatically initiate welfare action
❌ Replace welfare officers

🧑‍💼 Intervention Desk

When human review indicates that follow-up is appropriate:

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

The prototype records human review rather than allowing the ML model to execute an intervention automatically.

🗄️ Database

Manobal-AI uses MongoDB through the Motor async driver.

Personnel
   │
   ├── Welfare Records
   ├── Risk Assessments
   └── Intervention History

Data

Purpose

Personnel

Synthetic / demo personnel profiles

Welfare Records

Weekly welfare information

Risk Assessments

Model outputs and contextual results

Interventions

Human review and follow-up records

🧪 Synthetic Data & Validation

The current prototype is trained on synthetic data.

All demo personnel and organizational values are synthetic and labeled as demo data.

Synthetic Records
       ↓
Model Training
       ↓
LightGBM Artifact
       ↓
Prototype Inference
       ↓
Demo Welfare Signals

Before operational use, appropriately authorized data would require validation for calibration, false positives/negatives, subgroup performance, data quality, drift, privacy, security, and governance.

🏗️ Architecture

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
│ Welfare API │ Prediction │ History │ Intervention APIs     │
└───────────────┬──────────────────────────────┬──────────────┘
                │                              │
                ▼                              ▼
┌──────────────────────────┐       ┌──────────────────────────┐
│      ML INFERENCE        │       │         MONGODB          │
│ Feature Engineering      │       │ Personnel                │
│ Preprocessing            │       │ Assessments              │
│ LightGBM                 │       │ Interventions             │
│ Probabilities            │       │ Welfare Records           │
└──────────────────────────┘       └──────────────────────────┘

📦 Model Artifacts

artifacts/
├── risk_model.pkl
├── preprocessing_pipeline.pkl
├── baseline_model.pkl
├── model_metadata.json
└── MODEL_CARD.md

Artifact

Purpose

risk_model.pkl

Calibrated LightGBM classifier

preprocessing_pipeline.pkl

Runtime preprocessing transformer

baseline_model.pkl

Baseline model artifact

model_metadata.json

Feature ordering, bands, versions

MODEL_CARD.md

Intended use and limitations

🧩 Repository Structure

ProtoMano/
│
├── artifacts/
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
└── memory/
    └── SPEC.md

🔌 API

Local backend:

http://localhost:8001

Prediction

POST /api/predict

Demo Seeding

POST /api/demo/seed

Demo Personnel

GET /api/demo/personnel

The prediction endpoint accepts raw weekly records and performs feature engineering server-side.

🛠️ Technology Stack

Backend

Technology

Purpose

Python

Backend + ML ecosystem

FastAPI

REST API

Motor

Async MongoDB driver

MongoDB

Persistent data

LightGBM

Multiclass welfare classifier

scikit-learn

Preprocessing / calibration

joblib

Serialized model artifacts

pytest

Backend testing

Frontend

Technology

Purpose

Vite

Frontend tooling

React

User interface

TypeScript

Type safety

Machine Learning

Component

Purpose

LightGBM

Risk classification

Preprocessing Pipeline

Feature transformation

Calibration

Probability calibration

Feature Contributions

Model interpretation

Historical Heuristics

Trajectory / What Changed

Rule Logic

Welfare recommendations

🔐 Security & Privacy

Welfare-related information can be highly sensitive.

The production architecture should include:

Real authentication

Role-based access control

HTTPS

Secure database credentials

Secrets management

Restricted CORS

Rate limiting

Audit logging

Data minimization

Retention policies

Model governance

Privacy and security review

The current repository is a prototype and does not implement production authentication or RBAC.

🚀 Getting Started

Prerequisites

Install:

Python 3

pip

Node.js

Yarn

MongoDB

Git

Backend

git clone <repository-url>
cd ProtoMano
cd backend
pip install -r requirements.txt

Create:

backend/.env

Example:

MONGO_URL=mongodb://localhost:27017
DB_NAME=manobal_ai

Run:

uvicorn server:app --host 0.0.0.0 --port 8001 --reload

Backend:

http://localhost:8001

Frontend

cd frontend
yarn install
yarn dev

Frontend:

http://localhost:3000

Vite proxies /api to the backend.

🧪 Testing

Start the backend first, then from backend/:

pytest

For serial execution:

pytest -n 0

The backend tests cover welfare prediction, demo seeding, interventions, and reliability-oriented behavior.

🔄 End-to-End Workflow

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
         Data Trust            History
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

🗺️ Roadmap

Phase 1 — Core Prototype

FastAPI backend

React frontend

MongoDB integration

Model artifact loading

Welfare prediction API

Personnel workflow

Officer workspace

Demo data seeding

Intervention recording

Phase 2 — AI Decision Support

LightGBM integration

44-feature pipeline

Calibrated probabilities

Feature contributions

Data-trust heuristic

Risk + trust fusion

Historical trajectory

What Changed

Early-warning logic

Welfare recommendations

Phase 3 — Validation

Authorized real-world dataset validation

Calibration evaluation

False-positive / false-negative analysis

Subgroup performance analysis

Data-quality monitoring

Model drift detection

Model version tracking

Formal privacy review

Phase 4 — Production Readiness

Production authentication

RBAC

Secure sessions

HTTPS

Secrets management

Audit logging

Monitoring

Secure deployment

Governance framework

Phase 5 — Advanced Intelligence

Larger authorized datasets

Longitudinal modeling

Improved explainability

Human feedback loops

Privacy-preserving analytics

Advanced anomaly detection

Model drift monitoring

🧱 Design Principles

1. AI is decision support

The model produces signals; it does not make autonomous welfare decisions.

2. Human-in-the-loop

Human officers remain responsible for interpreting signals and determining appropriate follow-up.

3. Backend is the source of truth

Feature engineering and inference are performed server-side.

4. Data trust matters

Risk signals should be considered alongside data quality and trust.

5. Historical context matters

The platform considers trends and changes over time.

6. Explainability matters

Feature contributions and contextual changes can help officers understand the signal.

7. Privacy by design

Sensitive welfare information should be minimized, protected, and accessed through appropriate authorization.

8. Synthetic data during prototyping

The current model and demo use synthetic data.

9. No diagnosis

A welfare-risk signal is not a medical or psychological diagnosis.

10. No automated intervention

The platform supports human-led follow-up rather than executing autonomous action.

📊 Current Project Status

Status: Active SIH 2026 Prototype

Frontend                         ✅
FastAPI Backend                  ✅
MongoDB Integration              ✅
ML Artifact Loading              ✅
LightGBM Inference               ✅
44-Feature Pipeline              ✅
Risk Signal                      ✅
Class Probabilities              ✅
Feature Contributions            ✅
Data Trust                       ✅
Risk + Trust Fusion              ✅
Historical Trajectory            ✅
What Changed                     ✅
Welfare Recommendations          ✅
Demo Data Seeding                ✅
Officer Workspace                ✅
Intervention Recording           ✅
Production Authentication        ⏸️ Planned
Real-World Validation            ⏸️ Required
Production Deployment            ⏸️ Future

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
│ View Trajectory              │ Review What Changed            │
│ View Recommendations         │ Record Intervention             │
│ Privacy / Ethics             │ Follow-Up Workflow              │
└──────────────────────────────┴───────────────────────────────┘

🌐 Future Scalability

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

Potential future infrastructure:

Redis
Background Jobs
Model Serving
Observability
Audit Logging
Data Quality Monitoring
Model Drift Monitoring
Secure Cloud Deployment

🛡️ Responsible AI

Manobal-AI is designed around:

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

The current model uses synthetic data and is not validated for operational deployment.

🌱 Vision

Manobal-AI aims to make personnel welfare support more:

Proactive. Human-Centered. Explainable. Privacy-Aware. Data-Informed.

The long-term vision is not to replace welfare officers with AI.

It is to provide them with better information, better context, and better visibility into meaningful changes so that human-led welfare support can happen earlier and more thoughtfully.

              NOTICE EARLIER
                    ↓
             UNDERSTAND BETTER
                    ↓
              REVIEW HUMANLY
                    ↓
                  SUPPORT

❤️ Built for Smart India Hackathon 2026

Manobal-AI

Turning Welfare Signals into Human-Centered Support

AI should assist. Humans should decide.