# 🎯 Problem Statement

## The Challenge

Personnel serving in **Central Armed Police Forces (CAPFs), Armed Forces, and other uniformed services** operate in environments that can be physically demanding, psychologically stressful, and operationally hazardous.

Extended deployments, irregular working hours, workload pressures, separation from families, frequent transfers, training commitments, and exposure to difficult operational situations can contribute to **stress, emotional fatigue, burnout, and other welfare concerns**.

The current identification of such concerns often depends on **manual observation and voluntary self-reporting**. While these approaches remain important, they can make it difficult to consistently identify changes across large personnel populations and over extended periods.

The SIH problem statement therefore calls for an **AI-powered predictive personnel stress and welfare monitoring system** capable of identifying early indicators while maintaining privacy, confidentiality, dignity, and organizational trust.

---

## 🔎 The Existing Gap

The problem can be represented as:

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

The core challenge is therefore not simply **collecting more data**.

It is converting available and voluntarily provided welfare information into **structured, explainable signals that can help authorized welfare personnel identify meaningful changes and decide when human follow-up may be appropriate**.

---

# 💡 Proposed Solution — Manobal-AI

**Manobal-AI (Welfare Signal)** is a human-in-the-loop decision-support platform designed around the requirements of the SIH problem statement.

The platform brings together:

* Voluntary welfare check-ins
* Organizational and wellness indicators
* Historical assessment data
* Machine-learning based risk signaling
* Data-trust analysis
* Historical trajectory analysis
* “What Changed” insights
* Welfare recommendations
* Human officer review
* Intervention recording

into a unified welfare-support workflow.

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

Manobal-AI uses a **calibrated LightGBM multiclass classifier** to transform 44 engineered numerical features into a welfare-risk signal.

The system can incorporate indicators derived from the available welfare records and organizational context.

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

The model is **not presented as a diagnostic system**.

Instead, its output is treated as a **signal requiring appropriate human interpretation and review**.

---

# 🧠 From Prediction to Decision Support

A major design principle of Manobal-AI is that the model prediction is **only one component of the overall decision-support workflow**.

The platform combines:

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

The official SIH problem statement emphasizes welfare support while maintaining privacy and avoiding disciplinary misuse.

Manobal-AI therefore follows:

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

The system does **not** automatically:

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

Because welfare information can be highly sensitive, privacy is treated as a core architectural requirement rather than an additional feature.

The SIH problem statement specifically highlights:

* Privacy and confidentiality
* Prevention of stigmatization
* Reduction of false positives and false negatives
* Transparent and ethical AI
* Protection of sensitive welfare information
* Building trust among personnel

Manobal-AI reflects these requirements through:

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

The current repository remains a **prototype** and therefore does not yet implement production-grade authentication and RBAC.

---

# 📈 Expected Impact

The proposed system is intended to support the transition from a primarily reactive welfare workflow toward a more **proactive, preventive, and data-informed framework**.

Potential benefits identified in the SIH problem statement include:

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

The SIH problem statement also identifies potential benefits including improved welfare planning, workload management, workforce resilience, retention, job satisfaction, and reduction of incidents associated with prolonged occupational stress.

---

# 🎯 Manobal-AI's Core Objective

> **Manobal-AI aims to help authorized welfare personnel identify meaningful welfare signals earlier, understand the context behind those signals, and make more informed human-led follow-up decisions — while preserving privacy, dignity, and human oversight.**

The system therefore follows one fundamental principle:

```text
             AI SHOULD ASSIST.
             HUMANS SHOULD DECIDE.
```

---

## 📌 SIH Alignment

| SIH Requirement                        | Manobal-AI Implementation                               |
| -------------------------------------- | ------------------------------------------------------- |
| Personnel welfare monitoring           | Voluntary welfare check-ins                             |
| Predictive analytics                   | Calibrated LightGBM classifier                          |
| Stress / welfare risk assessment       | Low / Moderate / High welfare-risk signal               |
| Behavioral / organizational indicators | Engineered welfare and organizational features          |
| Welfare officer dashboard              | Officer command workspace                               |
| Early identification                   | Risk signal + historical trajectory                     |
| Intervention support                   | Human-reviewed intervention workflow                    |
| Privacy protection                     | Human-in-the-loop and controlled data flow              |
| Ethical AI                             | No diagnosis, discipline, or autonomous action          |
| Data-driven welfare planning           | Historical assessments and contextual insights          |
| Secure architecture                    | Server-side inference and backend-controlled processing |

---

# 🏁 In One Line

**Manobal-AI transforms voluntary welfare data into explainable welfare signals and contextual insights that help authorized officers identify changes earlier and provide appropriate human-led support.**
