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

## 🧠 The NLP Layer (spaCy)

The engine uses **spaCy** (Industry-standard NLP) to process manager feedback. Unlike simple keyword search, this system performs deep **Linguistic Dependency Analysis**.

### How & Why spaCy is Used:
1.  **Semantic Quantification**: It translates human sentiment into the numerical 1-5 proficiency scores required for matching.
2.  **Negation Detection**: Uses spaCy's **Dependency Parser** to find negations (e.g., *"lacks leadership"*). If detected, the competency is downgraded to **Level 1** regardless of what the knowledge map says.
3.  **Intensifier Boosting**: Detects positive qualifiers (e.g., *"expert"*, *"excellent"*). This allows the system to recognize "Expert" level performance mentioned in notes, boosting scores to **Level 5**.
4.  **Custom Phrase Matching**: Uses a `PhraseMatcher` to identify HR domain terms as first-class linguistic entities.

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
*   **Backend**: Python 3.10+ & FastAPI
*   **Data Models**: Pydantic (Strict Schema Enforcement)
*   **Quality**: Pytest (100% Logic Coverage)
