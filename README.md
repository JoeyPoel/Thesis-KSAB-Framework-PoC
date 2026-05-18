# Intelligent Talent Engine (SAP Concept)

A production-grade HR Microservice Proof-of-Concept (PoC) that automates talent matching and gap analysis using the **Skorková KSAB model**. This repository demonstrates how modern NLP can evolve legacy HR data into a holistic competency matrix.

> [!IMPORTANT]
> **PoC Status**: This is a conceptual architectural demonstration for a thesis project. It is designed to showcase "Intelligent ETL" and "Holistic Matching" logic. It is not a production-ready integration for SAP SuccessFactors, but a blueprint for one.

---

## 🎯 Project Purpose

Traditional HR systems often focus on "Paper Qualifications" (Certificates/Knowledge). This engine implements **Holistic Matching**, which weights Behaviors (B) and Abilities (A) equally with Knowledge (K) and Skills (S).

### Why this Repo?
*   **Thesis Defense**: Demonstrates Software Engineering competence in NLP-driven ETL and algorithmic orchestration.
*   **Legacy Data Mining**: Shows how to extract value from thousands of "dead" manager notes that are usually ignored in standard HR workflows.
*   **Decision Support**: Provides a mathematically grounded "Match Percentage" to help HR professionals spot talent that traditional filters would miss.

---

## 🧠 The NLP Layer & Secure Sanitization

The engine uses **spaCy** (Industry-standard NLP) to process manager feedback, enabling deep **Linguistic Dependency Analysis** and syntactic evaluation.

### How & Why spaCy & NLP are Used:
1.  **Semantic Quantification**: Translates unstructured qualitative human feedback into the numerical 1-5 proficiency levels required for matching.
2.  **Proximity Negation Detection**: Uses spaCy's **Dependency Parser** and a tokens-proximity window (8 tokens) to find negations (e.g., *"lacks leadership"*). If detected, the competency is downgraded to **Level 1** (Baseline).
3.  **Intensifier Boosting**: Detects positive qualifiers (e.g., *"expert"*, *"excellent"*, *"master"*). Recognizes "Expert" level performance in notes and boosts scores to **Level 5** (Expert).
4.  **Custom Phrase Matching**: Leverages a `PhraseMatcher` to identify HR competencies and KSAB categories as first-class entities.

### 🛡️ Multi-Layered Validation & Human-in-the-Loop (HITL)
To prevent "false security" and linguistic blindspots (like run-on text breaking dependency parsers), the ETL pipeline implements a highly robust, additive penalty scoring system. 

Each extracted competency starts with a baseline `validation_score` of `1.0`. Penalties are applied additively:
*   **Conflicting Signals (`-0.5`)**: Applied if a competency is simultaneously negated and intensified (e.g., *"shows no expert grasp"*).
*   **Ambiguous Language / Hedging (`-0.3`)**: Applied if the context contains hedging markers (e.g., *"maybe"*, *"possibly"*, *"somewhat"*, *"partially"*, *"unclear"*).
*   **Structural Complexity (Sentence Length)**:
    *   **`-0.15`** for moderately long sentences (>20 words) which make syntactic trees harder to parse.
    *   **`-0.30`** for rambling, run-on sentences (>40 words) that pose a high risk of parsing failures.

> [!IMPORTANT]
> If the final `validation_score` drops **below 0.75**, the record is automatically flagged with `requires_human_review = True`. This triggers the Human-in-the-Loop workflow, quarantining ambiguous or messy notes for HR review rather than passing them directly into matching calculations.

### 🌐 Multilingual Resilience & Automated Translation
To prevent NLP extraction failure on non-English manager notes (e.g., Dutch, German, Spanish, French), the pipeline integrates **deep-translator**:
*   **Auto-Detection & Normalization**: Transparently detects the source language and translates unstructured notes into English before running spaCy analysis.
*   **Robust Fallback Handling**: If translation APIs are unreachable or fail, the system implements a graceful `try-except` fallback, passing the raw notes to spaCy to ensure pipeline execution stability.

---

## 🏗️ Core Demo Scenarios (Edge Cases)

The engine is specifically tuned to handle "Complex" HR scenarios that fail in basic systems:

*   **The 'Brilliant Jerk'**: An employee with perfect technical scores but "hostile" behaviors detected via NLP. The engine downgrades their match for leadership roles.
*   **The 'Hidden Talent'**: An employee with low formal certifications but "excellent leadership" mentioned in manager notes. The engine surfaces them for promotion.
*   **The 'Skill Masker'**: Handles overqualified candidates by "capping" scores to prevent statistical skewing in gap analysis.
*   **The 'Career Pathfinder'**: Automatically maps an employee against the entire job catalog to find their ideal next step.

---

## 🚀 Getting Started

### Installation
1.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2.  Download the spaCy linguistic model:
    ```bash
    python -m spacy download en_core_web_sm
    ```

### Running the Engine
*   **Interactive Demo**: Run the scenario-based CLI to see the NLP and Matching logic in action.
    ```bash
    py demo.py
    ```
*   **Production API**: Start the FastAPI server for RESTful integration.
    ```bash
    py main.py
    ```
    *   Docs: `http://localhost:8000/docs`

### Cloud-Ready Deployment (Docker)
This microservice is containerized for consistent deployment:
1.  **Build and Run**:
    ```bash
    docker-compose up --build
    ```
2.  **Access Logs**: Internal engine logs are persisted to the `./logs` directory on your host machine.


---

## 🛠️ Technology Stack
*   **NLP**: spaCy (PhraseMatcher, Dependency Parsing)
*   **Translation**: deep-translator (Automated translation engine with robust failback)
*   **Backend**: Python 3.10+ & FastAPI
*   **Data Models**: Pydantic (Strict Schema Enforcement)
*   **Quality**: Pytest (100% Logic Coverage)
