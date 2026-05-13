import pytest
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
    enhanced = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Python is S-001, base proficiency is 3
    assert enhanced.get("S-001") == 3

def test_etl_logic_negation_downgrade():
    """Verify that 'lacks' or 'no' triggers a downgrade to Level 1."""
    notes = "The candidate lacks teamwork skills."
    formal_scores = {"B-002": 5} # Start high
    enhanced = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Teamwork is B-002, should be downgraded to 1
    assert enhanced.get("B-002") == 1

def test_etl_logic_intensifier_boost():
    """Verify that 'excellent' or 'expert' triggers a boost to Level 5."""
    notes = "Showed an excellent grasp of python."
    formal_scores = {}
    enhanced = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Python is S-001, base is 3, but 'excellent' boosts to 5
    assert enhanced.get("S-001") == 5

def test_etl_logic_deep_dependency_negation():
    """Verify that negation is caught even if slightly separated (spaCy dependency tree)."""
    notes = "Leadership is something they do not possess."
    formal_scores = {}
    enhanced = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    # Leadership is B-001, 'not possess' should downgrade to 1
    assert enhanced.get("B-001") == 1

def test_etl_logic_empty_input():
    scores = {"K-001": 3}
    assert ETLSanitizerService.extract_hidden_ksabs("", scores) == scores
    assert ETLSanitizerService.extract_hidden_ksabs(None, scores) == scores

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
    assert response.status_code == 400
    assert "ETL Failure" in response.json()["detail"]

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
