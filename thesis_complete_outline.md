# Comprehensive Thesis Outline: The Intelligent Talent Engine

This outline maps your entire codebase and the theoretical decisions behind it into a formal, highly detailed academic structure. Use this as the exact blueprint to write your thesis.

---

## Chapter 1: Introduction & Problem Statement
*   **1.1 The Context:** Modern enterprise HR relies on rigid Systems of Record (like SAP SuccessFactors) that track binary, formal skills but fail to capture holistic behaviors and hidden talents.
*   **1.2 The Problem:** Identifying true candidate fit requires complex mathematical mapping and unstructured data analysis (NLP), which cannot be safely or efficiently executed inside a legacy HR monolith without creating data silos or security vulnerabilities.
*   **1.3 The Proposed Solution:** Developing a stateless, external microservice "compute engine" that ingests HR data via REST API, applies the Skorková Holistic Competence Model, and outputs deterministic gap analysis and training recommendations.

---

## Chapter 2: Theoretical Framework
*   **2.1 The Skorková Holistic Competence Model:** 
    *   Define KSAB (Knowledge, Skill, Ability, Behaviour).
    *   Explain why evaluating Behaviour (e.g., Psychological Safety) is mathematically as critical as formal Knowledge (e.g., Python).
*   **2.2 Microservice Orthogonality vs. Monoliths:** 
    *   Discuss the theory of "Stateless Compute Engines."
    *   Argue why this PoC simulates SAP OData JSON payloads rather than directly reading a SQL database (Proof of Concept boundary).

---

## Chapter 3: Software Engineering & Architecture (The Codebase)
*What to write: Explain how the PoC was engineered to production-grade standards.*
*   **3.1 The Service Layer Pattern (`main.py` vs `services/`):**
    *   Explain the decoupling of the HTTP router (`main.py`) from the business logic (`services/etl.py` and `services/matching.py`). 
    *   *Theory:* High cohesion, low coupling, and testability.
*   **3.2 Domain-Driven Design (DDD) with Python (`models/domain.py`):**
    *   Explain the transition from loose JSON dictionaries to strict `Pydantic` classes (`Job`, `Course`, `EmployeeInternal`, `KSAB`).
    *   *Code Reference:* Show how `KSAB` uses Regex (`^[KSAB]-\d{3}$`) to prevent dirty data.
    *   *Code Reference:* Show how `main.py` enforces Referential Integrity by cross-referencing `DB_KSABS` before allowing an update.

---

## Chapter 4: Data Privacy, Security, and GDPR Compliance
*What to write: How the system handles sensitive HR evaluations legally and securely.*
*   **4.1 Active PII Scrubbing (Data Minimization):**
    *   *Theory:* Cite GDPR Article 5(1)(c).
    *   *Code Reference:* Explain how `ETLSanitizerService.process_employee()` explicitly overwrites `employee.name = None` and `employee.email = None` before the math engine runs, ensuring algorithmic neutrality.
*   **4.2 Cryptographic Response Masking:**
    *   *Code Reference:* Contrast `EmployeeInternal` (which holds sensitive manager notes) with the `CareerRecommendationResponse` (which strips notes out).
    *   *Theory:* Guaranteeing that internal reviews never leak via API serialization.
*   **4.3 Role-Based Access Control (RBAC):**
    *   *Code Reference:* Detail the `require_role` dependency in `main.py`.
    *   *Theory:* Principle of Least Privilege. Explain how the system inspects the `X-User-Role` HTTP header to block Employees from using Manager/Recruiter endpoints (`403 Forbidden`).

---

## Chapter 5: The Algorithmic Engine (Mathematical Models)
*What to write: The core logic inside `services/matching.py`.*
*   **5.1 Natural Language Processing Simulation (The ETL Layer):**
    *   Explain how `ETLSanitizerService` uses keyword extraction to map unstructured manager notes into formal KSAB proficiency points.
*   **5.2 Gap Analysis and Overqualification Bounding:**
    *   *The Problem:* "Skill Masking" (The Brilliant Jerk scenario). High coding skills shouldn't hide toxic behavior.
    *   *The Math:* $S_k = \min(E_k, R_k)$. 
    *   *Code Reference:* Explain `calculate_match_percentage()` and how the `min()` function caps over-performance to its required baseline.
*   **5.3 Pathfinding via The Greedy Algorithm:**
    *   *Code Reference:* The `recommend_courses()` function.
    *   *Theory & Complexity:* Explain why a Greedy Algorithm was chosen over Dijkstra's. Detail the Time Complexity of $O(K \times C)$ (where K = missing skills, C = course catalogue). Justify that corporate catalogues are flat, making Greedy the fastest and most deterministic choice for real-time APIs.

---

## Chapter 6: Validation, Edge Cases & Quality Assurance
*What to write: Proving the engine actually works exactly as intended.*
*   **6.1 Scenario Validation (The 7 Edge Cases from `demo.py`):**
    *   *Scenario 1: The Brilliant Jerk.* Proves the NLP downgrades behavioral scores, ruining the perfect formal match.
    *   *Scenario 2: Hidden Talent.* Proves NLP finds unrecorded leadership skills, triggering a match.
    *   *Scenario 3: Missing Cert.* Standard gap identification.
    *   *Scenario 4: Skill Masker.* Proves the $S_k = \min(E_k, R_k)$ formula works.
    *   *Scenario 5: Blank Slate.* Proves the system handles new hires with zero formal data.
    *   *Scenario 6 & 7: Pathfinder & Candidate Finder.* Proves the engine scales horizontally across massive datasets.
*   **6.2 Automated Testing and CI/CD:**
    *   *Code Reference:* `test_main.py` achieving 100% Pytest coverage (21 tests).
    *   *Code Reference:* `.gitlab-ci.yml`. Explain the "Fail-Fast" DevOps methodology (linting with `flake8`, running tests on push) to prevent regressions in mathematical models.

---

## Chapter 7: Conclusion
*   **7.1 Summary of Achievements:** The PoC successfully demonstrates that complex competency modeling can be achieved securely outside of legacy HR systems.
*   **7.2 Future Work:** Integrating real Machine Learning/LLMs for the NLP extraction rather than regex mapping; connecting the endpoints to a live SAP OData sandbox.
