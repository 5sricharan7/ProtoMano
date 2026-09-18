<div align="center">

# 🎯 Manobal-AI — Problem Statement & Solution

### AI-Assisted Personnel Welfare Intelligence & Human-in-the-Loop Decision Support

**Smart India Hackathon 2026 • Problem Statement 26186**

> **AI should assist. Humans should decide.**

</div>

---

## 📌 Executive Summary

Personnel serving in **Central Armed Police Forces (CAPFs), Armed Forces, and other uniformed services** operate in environments that can be physically demanding, psychologically stressful, and operationally hazardous.

Manobal-AI proposes a **human-in-the-loop welfare decision-support platform** that converts voluntary welfare information and authorized organizational indicators into structured, contextual welfare signals.

The platform combines:

- Voluntary welfare check-ins
- Organizational and wellness indicators
- Server-side feature engineering
- A 44-feature ML pipeline
- Calibrated LightGBM inference
- Class probabilities
- Data-trust analysis
- Historical trajectory analysis
- **What Changed** insights
- Welfare recommendations
- Authorized human officer review
- Human-reviewed intervention recording

The system is deliberately designed to support **early awareness and informed welfare follow-up**, rather than autonomous personnel decision-making.

---

## 🧭 Problem at a Glance

```text
Operational Environment
        │
        ├── Extended Deployments
        ├── Irregular Duty Hours
        ├── Workload Pressure
        ├── Leave / Transfer Patterns
        ├── Training Commitments
        ├── Family Separation
        └── Other Welfare Indicators
        │
        ▼
     Personnel
        │
        ▼
 ┌──────────────────────┐
 │ Manual Observation   │
 │        +             │
 │ Self-Reporting       │
 └──────────┬───────────┘
            │
            ▼
     Limited Visibility
            │
            ▼
 Potential Changes May Be
 Difficult To Identify Early
```

### The Core Challenge

The challenge is not simply **collecting more data**.

It is converting available and voluntarily provided welfare information into:

> **Structured, explainable signals that can help authorized welfare personnel identify meaningful changes and decide when human follow-up may be appropriate.**

---

# 💡 Proposed Solution — Manobal-AI

**Manobal-AI (Welfare Signal)** is a human-in-the-loop decision-support platform designed around the requirements of the SIH problem statement.

It brings together:

```text
Voluntary Welfare Check-ins
            +
Organizational / Wellness Indicators
            +
Historical Assessment Data
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
            +
Intervention Recording
```

into a unified welfare-support workflow.

### Core Workflow

```text
                  MANOBAL-AI
                      │
                      ▼
             Voluntary Check-In
                      │
                      ▼
              Weekly Welfare Data
                      │
                      ▼
             Feature Engineering
                      │
                      ▼
                  ML Model
                      │
                      ▼
          ┌───────────────────────┐
          │ Welfare-Risk Signal   │
          │                       │
          │ Low / Moderate / High │
          └───────────┬───────────┘
                      │
              ┌───────┴───────┐
              ▼               ▼
         Data Trust       History
              │               │
              └───────┬───────┘
                      ▼
                Risk + Trust
                   Fusion
                      │
            ┌─────────┼─────────┐
            ▼         ▼         ▼
         REVIEW    MONITOR   VERIFY DATA
            │
            ▼
       Human Officer
           Review
            │
            ▼
       Follow-Up /
       Intervention
```

---

# 🤖 What Does the AI Actually Do?

Manobal-AI uses a **calibrated LightGBM multiclass classifier** to transform **44 engineered numerical features** into a welfare-risk signal.

```text
Raw Welfare Records
        │
        ▼
Server-Side Feature Engineering
        │
        ▼
44 Numerical Features
        │
        ▼
Preprocessing Pipeline
        │
        ▼
Calibrated LightGBM
        │
        ▼
Class Probabilities
        │
        ▼
Low / Moderate / High
Welfare-Risk Signal
```

### AI Boundary

The model is **not presented as a diagnostic system**.

Its output is treated as:

> **An AI-assisted signal requiring appropriate human interpretation and review.**

The platform therefore separates:

```text
                    MODEL
                      │
                      ▼
                Risk Signal
                      │
                      ▼
              Contextual Analysis
                      │
                      ▼
                Human Officer
                      │
                      ▼
                Human Decision
```

---

# 🧠 From Prediction to Decision Support

A major design principle is that the ML prediction is **only one component** of the overall decision-support workflow.

Manobal-AI combines:

```text
                  ML Risk Signal
                        │
                        +
                  Data Trust
                        │
                        +
              Historical Trajectory
                        │
                        +
                  What Changed
                        │
                        ▼
                Contextual Signal
                        │
                        ▼
               Human Officer Review
```

This allows the system to provide additional context around a signal instead of presenting a single prediction without explanation.

---

# 🛡️ Human-in-the-Loop by Design

The platform is deliberately designed around human review.

```text
AI
 │
 │ identifies a signal
 ▼
Welfare Officer
 │
 │ reviews context
 ▼
Human Decision
 │
 │ determines appropriate response
 ▼
Welfare Follow-Up
```

### 🚫 What the System Does NOT Do

```text
❌ Diagnose personnel
❌ Predict self-harm
❌ Take disciplinary action
❌ Automatically contact personnel
❌ Automatically initiate an intervention
❌ Replace welfare officers
```

This keeps the platform focused on **early awareness and welfare support**, rather than automated personnel decision-making.

---

# 🔐 Privacy & Trust

Welfare information can be highly sensitive. Privacy is therefore treated as a **core architectural requirement**, not an additional feature.

The SIH problem statement highlights:

- Privacy and confidentiality
- Prevention of stigmatization
- Reduction of false positives and false negatives
- Transparent and ethical AI
- Protection of sensitive welfare information
- Building trust among personnel

### Controlled Data Flow

```text
Voluntary Data
      ↓
Controlled Access
      ↓
Secure Backend Processing
      ↓
Model Inference
      ↓
Human Review
      ↓
Explicit Welfare Action
```

### Prototype Boundary

The current repository remains a **prototype** and therefore does not yet implement production-grade authentication and RBAC.

---

# 📈 Expected Impact

The proposed system is intended to support a transition from a primarily reactive welfare workflow toward a more:

**Proactive • Preventive • Data-Informed**

framework.

### Intended Support Flow

```text
Early Identification
        ↓
Timely Welfare Review
        ↓
Better Support
        ↓
Improved Personnel Well-Being
        ↓
Greater Workforce Resilience
        ↓
Improved Operational Readiness
```

The SIH problem framing also identifies potential benefits around:

- Welfare planning
- Workload management
- Workforce resilience
- Retention
- Job satisfaction
- Reduction of incidents associated with prolonged occupational stress

These represent **intended or potential benefits**, not claims of measured real-world impact from the current prototype.

---

# 🎯 Manobal-AI's Core Objective

> **Manobal-AI aims to help authorized welfare personnel identify meaningful welfare signals earlier, understand the context behind those signals, and make more informed human-led follow-up decisions — while preserving privacy, dignity, and human oversight.**

The system therefore follows one fundamental principle:

```text
             AI SHOULD ASSIST.
             HUMANS SHOULD DECIDE.
```

---

# 📊 SIH Alignment

| SIH Requirement | Manobal-AI Implementation |
|---|---|
| **Personnel welfare monitoring** | Voluntary welfare check-ins |
| **Predictive analytics** | Calibrated LightGBM classifier |
| **Stress / welfare risk assessment** | Low / Moderate / High welfare-risk signal |
| **Behavioral / organizational indicators** | Engineered welfare and organizational features |
| **Welfare officer dashboard** | Officer command workspace |
| **Early identification** | Risk signal + historical trajectory |
| **Intervention support** | Human-reviewed intervention workflow |
| **Privacy protection** | Human-in-the-loop and controlled data flow |
| **Ethical AI** | No diagnosis, discipline, or autonomous action |
| **Data-driven welfare planning** | Historical assessments and contextual insights |
| **Secure architecture** | Server-side inference and backend-controlled processing |

---

# 🔬 Technical Differentiator

Manobal-AI is not positioned around the ML model alone.

The technical workflow extends beyond:

```text
DATA
 ↓
MODEL
 ↓
PREDICTION
```

to:

```text
DATA
 ↓
CANONICAL FEATURE ENGINEERING
 ↓
44-FEATURE MODEL CONTRACT
 ↓
CALIBRATED ML INFERENCE
 ↓
RISK PROBABILITIES
 ↓
DATA TRUST
 ↓
HISTORICAL CONTEXT
 ↓
WHAT CHANGED
 ↓
RISK + TRUST FUSION
 ↓
WELFARE RECOMMENDATIONS
 ↓
HUMAN REVIEW
 ↓
FOLLOW-UP
```

This creates a distinction between **AI inference** and the broader **decision-support platform**.

---

# 🧩 Architectural Principles

### 1. Human Before Automation

AI provides support; authorized humans retain decision authority.

### 2. Welfare Before Discipline

The platform is designed around welfare support rather than disciplinary classification.

### 3. Context Before Conclusion

Signals are accompanied by history, trust, and change information.

### 4. Explainability

The system can expose probabilities and feature contributions when available.

### 5. Data Awareness

The quality and completeness of input information are considered alongside model output.

### 6. Backend Authority

Feature engineering and model inference remain server-side.

### 7. Privacy by Design

Sensitive welfare information should be appropriately protected and accessed through authorized workflows.

### 8. Responsible Deployment

Synthetic-data demonstration is clearly separated from future operational deployment.

---

# ⚠️ Important Prototype Boundary

The current implementation is an **SIH prototype**.

It should not be interpreted as an operationally validated welfare-management system.

Before operational use, the platform would require appropriate:

- Authorized real-world data validation
- Calibration evaluation
- False-positive / false-negative analysis
- Subgroup performance evaluation
- Data-quality validation
- Privacy review
- Security assessment
- Authentication and RBAC
- Governance controls
- Auditability
- Model monitoring
- Operational safety review

### Current Data Boundary

```text
Current Prototype
      │
      ▼
Synthetic Demonstration Data
      │
      ▼
Prototype Model Inference
      │
      ▼
Demonstration Welfare Signals
```

Any future operational system would need a separately governed and validated data pipeline.

---

# 🏁 In One Line

> **Manobal-AI transforms voluntary welfare data into explainable welfare signals and contextual insights that help authorized officers identify changes earlier and provide appropriate human-led support.**

---

# ❤️ Final Principle

<div align="center">

## AI SHOULD ASSIST.

## HUMANS SHOULD DECIDE.

**Manobal-AI — Turning welfare signals into human-centered support.**

**Smart India Hackathon 2026**

</div>
