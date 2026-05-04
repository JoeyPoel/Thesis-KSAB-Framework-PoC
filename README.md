# Intelligent Talent Engine (Proof of Concept)

This repository contains the technical Proof of Concept (PoC) for an HBO ICT Software Engineering graduation project. It demonstrates the "Intelligent Services" layer of a modern HR system, designed to replace siloed HR modules with an integrated talent matching engine.

## Theoretical Framework

The engine is built around the **Skorková Holistic Competence Model**, formulated as:
`HQ = f(SQ, AQ, KQ)` *(Human Quality = function of Social Quality, Application Quality, and Knowledge Quality)*.

To make this computable, the model maps directly to a strict **KSAB Taxonomy**:
*   **K (Knowledge / KQ)**: Formal education and certifications (e.g., Data Science, Agile).
*   **S (Skills / AQ)**: Learned technical proficiencies applied in daily work (e.g., Python, SAP).
*   **A (Abilities / AQ)**: Innate or developed cognitive traits (e.g., Complex Problem Solving).
*   **B (Behaviours / SQ)**: Character, ethics, teamwork, and moral maturity (e.g., Empathy, Psychological Safety).

Unlike traditional systems that only measure binary technical skills (Has Python? Yes/No), this PoC measures **proficiency levels (1-5)** across all holistic dimensions, ensuring a balanced evaluation of the "whole human."

## How It Works: System Architecture

The PoC is broken down into modular components that handle the entire lifecycle from messy legacy HR data to automated career recommendations.

### 1. The Data Layer (`mock_data.py`)
Provides the simulated database representing a corporate environment. It features:
*   A **Job Catalogue** detailing specific roles and their holistic KSAB requirements (e.g., Leadership heavily weighting Behaviours).
*   A **Course Catalogue** that maps learning interventions to specific KSAB IDs.
*   **Employee Profiles** containing both formal structured scores and unstructured manager notes. This dataset intentionally includes edge cases like the "Brilliant Jerk" (perfect technicals, terrible behaviors) and the "Hidden Gem" (low formal scores, but high informal leadership traits).

### 2. ETL & Sanitization Pipeline (`etl.py`)
Real HR data is rarely clean. The ETL script simulates an ingestion pipeline that reads raw employee profiles and applies simulated NLP (Natural Language Processing).
*   **Hidden Skill Extraction**: It scans unstructured `manager_unstructured_notes` for keywords. When a manager mentions that an employee "organizes large community events," the pipeline parses this text and dynamically injects the hidden behaviour score (`S-004: Level 4`) into the employee's profile.
*   **Data Preservation**: It creates an `enhanced_ksab_scores` dictionary without destroying the original legacy notes, adhering to data warehousing best practices.

### 3. The Math Engine (`algorithm.py`)
This is the deterministic core of the engine. It abandons simple binary matching for a weighted scalar calculation.
*   **Match Calculation**: It calculates overlap based on required vs. actual proficiency.
*   **Overqualification Capping**: Earned points are capped at the required level. This mathematically prevents an employee with a Level 5 in Python from masking a Level 1 in Teamwork. A "Brilliant Jerk" will never achieve a 100% match for a leadership role.
*   **Targeted Gap Analysis**: It identifies the exact point deficit for every missing KSAB and queries the `Course Catalogue` to recommend the minimum set of training required to close the specific holistic gap.

### 4. API Middleware (`main.py`)
The system is wrapped in a modern FastAPI application, providing standard RESTful endpoints.
*   `POST /api/etl/sanitize`: Ingests and enhances legacy data.
*   `POST /api/skills/update`: Allows structured updates, using Pydantic regex validation to reject unstructured text (enforcing the strict `[KSAB]-\d{3}` schema).
*   `GET /api/career/recommendations/{employee_id}`: The primary endpoint that runs the math engine to find the employee's best internal mobility match and outputs the required training interventions.

### 5. Automated Testing (`test_main.py`)
A Pytest suite that proves the math works. It mathematically verifies the proficiency calculations, gap detection, and tests the edge-case inputs to ensure API reliability.

## Interactive Demo (`demo.py`)
To easily demonstrate the logic for a thesis defense, the PoC includes a visual CLI script. 

Run `python demo.py` to interactively test 5 distinct edge cases that prove the validity of the Skorková holistic model:
1. **The 'Paper Tiger'**: Demonstrates the NLP pipeline catching toxic behavioral traits in unstructured notes and actively *downgrading* a formal perfect score.
2. **The 'Hidden Talent'**: Shows how the NLP pipeline can find hidden leadership traits in formal text and boost an employee's match score.
3. **The 'Missing Cert'**: Demonstrates the engine accurately isolating exactly one missing point for a knowledge trait, and successfully recommending the specific course needed to close that gap.
4. **The 'Skill Masker'**: Mathematically proves that the engine caps overqualification (earning 15 points in a skill that only requires 5 points will not artificially hide a 0 score in teamwork).
5. **The 'Blank Slate'**: Shows the engine creating a baseline profile out of thin air for a new hire with zero formal HR data, using only their onboarding notes.

## Thesis Defense: PoC vs. Production Architecture

If you are defending this project, it is critical to explain the "hidden logic" and how this Proof of Concept scales to a real-world enterprise environment:

### 1. NLP Simulation vs. Real AI (The ETL Layer)
*   **In this PoC**: The NLP is simulated using a hardcoded dictionary (`KSAB_KEYWORD_MAP` in `mock_data.py`). When the script sees the exact string `"hostile environment"`, it blindly assigns `B-001: Level 1`.
*   **In Production**: The `extract_hidden_ksabs` function would pass the unstructured text to a **Large Language Model (LLM)** or a dedicated **Sentiment Analysis Engine**. The LLM would be prompted to identify any KSABs and dynamically grade the proficiency based on the adjective severity (e.g., scoring a `5` for "expert" vs a `1` for "toxic"). The PoC proves that *if* the NLP layer outputs a score, the pipeline will process it securely.

### 2. The Proficiency Capping (The Math Engine)
Traditional applicant tracking systems add up all skills to create a final score. This is highly flawed because a candidate with `Level 5 Python` and `Level 1 Teamwork` will mathematically beat a candidate with `Level 3 Python` and `Level 3 Teamwork`. 
*   **The Hidden Logic**: In `algorithm.py`, the `calculate_match_percentage` function uses `min(emp_level, req_level)`. This actively *caps* the points earned at the required level. 
*   **Why it matters**: It mathematically prevents **Overqualification Masking**. A toxic but brilliant engineer cannot hide their behavioral gaps behind their technical prowess.

### 3. Data Preservation (Data Warehousing Best Practices)
*   **The Hidden Logic**: When transforming the unstructured manager notes into rigid KSAB codes, the original text is deliberately *not* deleted. Instead, the formal scores are copied and extended into an `enhanced_ksab_scores` dictionary.
*   **Why it matters**: Legacy unstructured data is a goldmine. As NLP models improve in the future, you will want to re-run your ETL pipeline over historical data to extract deeper insights. Destroying raw data during sanitization violates strict HR data warehousing principles.

## Getting Started

### Prerequisites
Make sure you have Python 3.10+ installed.

### Installation
1.  Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Running the Application
1.  Start the FastAPI server:
    ```bash
    python main.py
    ```
2.  Open your browser and navigate to:
    *   **Interactive API Docs (Swagger UI)**: `http://localhost:8000/docs`
    *   **Redoc**: `http://localhost:8000/redoc`

### Running the Tests
To verify the engine's core logic, run the test suite:
```bash
pytest test_main.py
```
