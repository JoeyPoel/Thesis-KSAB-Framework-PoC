# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient
from main import app, DB_EMPLOYEES, DB_JOBS
from services.matching import MatchingEngineService
from services.etl import ETLSanitizerService
from models.domain import EmployeeInternal, Course, Job

client = TestClient(app)

# -----------------------------------------
# Database Bootstrap Tests
# -----------------------------------------
def test_bootstrap_db_failure(monkeypatch):
    import main
    # Mock data to something invalid to trigger exception
    monkeypatch.setattr(main, "EMPLOYEE_PROFILES", [{"invalid_data": "causes_error"}])
    main.bootstrap_db()
    assert main.DB_EMPLOYEES == []
    
    # Restore the database for other tests
    monkeypatch.undo()
    main.bootstrap_db()

# -----------------------------------------
# RBAC Security Tests
# -----------------------------------------
def test_rbac_skills_update_employee_forbidden():
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "K-001", "proficiency": 4},
        headers={"X-User-Role": "employee"}
    )
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]

def test_rbac_candidates_employee_forbidden():
    response = client.get("/api/candidates/best-match/J-002", headers={"X-User-Role": "employee"})
    assert response.status_code == 403

# -----------------------------------------
# Algorithm Tests (Matching Engine)
# -----------------------------------------
def test_calculate_match_percentage():
    employee_scores = {"K-002": 2, "S-002": 3, "A-002": 4}
    required_ksabs = {"K-002": 4, "S-002": 3, "A-002": 2}
    
    match_pct = MatchingEngineService.calculate_match_percentage(employee_scores, required_ksabs)
    assert round(match_pct, 2) == 77.78
    
    gaps = MatchingEngineService.calculate_skill_gaps(employee_scores, required_ksabs)
    assert gaps == {"K-002": 2}

def test_calculate_match_percentage_empty_requirements():
    assert MatchingEngineService.calculate_match_percentage({}, {}) == 100.0

def test_overqualification_capping():
    required = {"S-001": 5, "S-002": 5}
    employee = {"S-001": 10, "S-002": 1}
    match_pct = MatchingEngineService.calculate_match_percentage(employee, required)
    assert match_pct == 60.0

def test_recommend_courses_no_coverage():
    missing_ksabs = ["K-999"]
    course_catalogue = [Course(course_id="C-001", title="Test", type="Test", target_ksab_ids=["K-001"])]
    recommendations = MatchingEngineService.recommend_courses(missing_ksabs, course_catalogue)
    assert recommendations == []

# -----------------------------------------
# NLP Service Tests (spaCy Logic)
# -----------------------------------------
def test_etl_logic_neutral_mention():
    """Verify that a neutral mention takes the base level from the knowledge map."""
    notes = "John works with python."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Python is S-001, base proficiency is 3
    assert enhanced.get("S-001") == 3

def test_etl_logic_negation_downgrade():
    """Verify that 'lacks' or 'no' triggers a downgrade to Level 1."""
    notes = "The candidate lacks teamwork skills."
    formal_scores = {"B-002": 5} # Start high
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Teamwork is B-002, should be downgraded to 1
    assert enhanced.get("B-002") == 1

def test_etl_logic_intensifier_boost():
    """Verify that 'excellent' or 'expert' triggers a boost to Level 5."""
    notes = "Showed an excellent grasp of python."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Python is S-001, base is 3, but 'excellent' boosts to 5
    assert enhanced.get("S-001") == 5

def test_etl_logic_deep_dependency_negation():
    """Verify that negation is caught even if slightly separated (spaCy dependency tree)."""
    notes = "Leadership is something they do not possess."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Leadership is B-001, 'not possess' should downgrade to 1
    assert enhanced.get("B-001") == 1

def test_etl_logic_empty_input():
    scores = {"K-001": 3}
    assert ETLSanitizerService.extract_hidden_ksabs("", scores) == (scores, False)
    assert ETLSanitizerService.extract_hidden_ksabs(None, scores) == (scores, False)

def test_etl_process_employee_anonymization():
    """Verify GDPR anonymization during ETL."""
    emp = EmployeeInternal(
        employee_id="E-001",
        name="John Doe",
        email="john@example.com",
        manager_unstructured_notes="Expert python developer",
        formal_ksab_scores={}
    )
    processed = ETLSanitizerService.process_employee(emp)
    assert processed.name is None
    assert processed.email is None
    assert processed.enhanced_ksab_scores["S-001"] == 5

def test_etl_logic_implicit_negation_trap():
    """Verify that implicit negation traps like 'far from' are detected, negated, and flagged."""
    notes = "They are far from expertly managing teamwork."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # teamwork is B-002, should be downgraded to 1 due to implicit negation, and flagged for human review
    assert enhanced.get("B-002") == 1
    assert requires_review is True

def test_etl_logic_misaligned_intensifier():
    """Verify that misaligned intensifiers (like intensifier neutralized by potential/concessives) are flagged."""
    notes = "They have the potential to expertly use python."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Python is S-001. Since 'potential' is a neutralizing context, it should trigger low confidence / human review
    assert requires_review is True

def test_etl_logic_semantic_paradox():
    """Verify that double negatives/semantic paradoxes don't downgrade the skill and are flagged for review."""
    notes = "They rarely fail to show natural leadership."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Leadership is B-001. 'rarely fail to' is positive, so it should not be downgraded (remains >= base default 5), but flags for review
    assert enhanced.get("B-001") is not None
    assert enhanced.get("B-001") != 1
    assert requires_review is True

def test_etl_logic_negated_intensifier_partial_downgrade():
    """Verify that a negated intensifier (e.g. 'not expertly') triggers a partial downgrade to 2.5 and flags for review."""
    notes = "They manage teamwork but not expertly."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # teamwork is B-002, should be downgraded to 2.5 because of 'not expertly'
    assert enhanced.get("B-002") == 2.5
    assert requires_review is True

def test_etl_logic_decent_not_expert():
    """Verify that a phrase containing 'decent' but 'not expert' triggers a 2.5 score and flags for review."""
    notes = "Their teamwork is decent but they are not an expert."
    formal_scores = {}
    enhanced, requires_review = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # teamwork is B-002, should be downgraded to 2.5
    assert enhanced.get("B-002") == 2.5
    assert requires_review is True

def test_etl_logic_negated_intensifier_gap_and_course():
    """Verify that a 2.5 proficiency creates a gap against required level 4 and recommends a course."""
    employee_scores = {"B-002": 2.5}
    required_ksabs = {"B-002": 4.0}
    
    match_pct = MatchingEngineService.calculate_match_percentage(employee_scores, required_ksabs)
    # 2.5 / 4.0 = 62.5%
    assert match_pct == 62.5
    
    gaps = MatchingEngineService.calculate_skill_gaps(employee_scores, required_ksabs)
    assert gaps == {"B-002": 1.5}
    
    # Empathy Workshop (C-004) targets B-002
    course_catalogue = [Course(course_id="C-004", title="Empathy Workshop", type="Classroom", target_ksab_ids=["B-002"])]
    recommendations = MatchingEngineService.recommend_courses(list(gaps.keys()), course_catalogue)
    assert "C-004" in recommendations

# -----------------------------------------
# API Endpoints Tests
# -----------------------------------------
def test_update_skills_valid():
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "K-001", "proficiency": 4},
        headers={"X-User-Role": "manager"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_update_skills_employee_not_found():
    response = client.post(
        "/api/skills/update?employee_id=NON-EXISTENT",
        json={"ksab_id": "K-001", "proficiency": 4},
        headers={"X-User-Role": "manager"}
    )
    assert response.status_code == 404

def test_update_skills_ksab_not_found():
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "K-999", "proficiency": 4},
        headers={"X-User-Role": "manager"}
    )
    assert response.status_code == 400
    assert "does not exist in the catalogue" in response.json()["detail"]

def test_endpoint_etl_sanitization_intensified():
    payload = [
        {
            "employee_id": "E-TEST",
            "formal_ksab_scores": {"K-001": 5},
            "manager_unstructured_notes": "excellent grasp of python"
        }
    ]
    response = client.post("/api/etl/sanitize", json=payload, headers={"X-User-Role": "recruiter"})
    assert response.status_code == 200
    data = response.json()[0]
    # Now expects 5 because of 'excellent'
    assert data["enhanced_ksab_scores"]["S-001"] == 5

def test_endpoint_pathfinder():
    response = client.get("/api/career/recommendations/E-002", headers={"X-User-Role": "employee"})
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "E-002"
    assert "match_percentage" in data

def test_endpoint_candidate_finder():
    response = client.get("/api/candidates/best-match/J-002", headers={"X-User-Role": "recruiter"})
    assert response.status_code == 200
    data = response.json()
    assert data["target_job_id"] == "J-002"

def test_get_recommendations_employee_not_found():
    response = client.get("/api/career/recommendations/NON-EXISTENT", headers={"X-User-Role": "employee"})
    assert response.status_code == 404

def test_get_recommendations_job_not_found():
    response = client.get("/api/career/recommendations/E-001?target_job_id=NON-EXISTENT", headers={"X-User-Role": "manager"})
    assert response.status_code == 404

def test_get_best_candidate_job_not_found():
    response = client.get("/api/candidates/best-match/NON-EXISTENT", headers={"X-User-Role": "manager"})
    assert response.status_code == 404

def test_sanitize_data_error_handling(monkeypatch):
    import services.etl
    def mock_process_employee(emp):
        raise Exception("ETL Failure")
    monkeypatch.setattr(services.etl.ETLSanitizerService, "process_employee", mock_process_employee)
    
    payload = [{"employee_id": "E-TEST", "formal_ksab_scores": {}}]
    response = client.post("/api/etl/sanitize", json=payload, headers={"X-User-Role": "manager"})
    assert response.status_code == 422
    assert "ETL Failure" in response.json()["reason"]

def test_get_recommendations_no_suitable_job(monkeypatch):
    import main
    monkeypatch.setattr(main, "DB_JOBS", [])
    response = client.get("/api/career/recommendations/E-001", headers={"X-User-Role": "employee"})
    assert response.status_code == 404

def test_get_best_candidate_no_candidate(monkeypatch):
    import main
    monkeypatch.setattr(main, "DB_EMPLOYEES", [])
    response = client.get("/api/candidates/best-match/J-001", headers={"X-User-Role": "recruiter"})
    assert response.status_code == 404
