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

def test_etl_logic():
    notes = "This employee creates a hostile environment but natural leadership is visible."
    formal_scores = {"K-001": 3}
    
    enhanced = ETLSanitizerService.extract_hidden_ksabs(notes, formal_scores)
    assert "B-001" in enhanced
    assert enhanced["B-001"] == 1
    assert enhanced["K-001"] == 3

def test_etl_logic_non_string_input():
    scores = {"K-001": 3}
    assert ETLSanitizerService.extract_hidden_ksabs(None, scores) == scores

def test_missing_baseline_data_edge_case():
    employee = EmployeeInternal(
        employee_id="EMP-NO-DATA",
        formal_ksab_scores={},
        enhanced_ksab_scores={}
    )
    target_job = Job(
        job_id="J-101",
        title="Test Job",
        department="Test Dept",
        required_ksabs={"K-001": 3}
    )
    course_catalogue = [
        Course(course_id="C-001", title="Test", type="Test", target_ksab_ids=["K-001"])
    ]
    
    result = MatchingEngineService.evaluate_employee_for_role(employee, target_job, course_catalogue)
    assert result.match_percentage == 0.0
    assert result.missing_ksabs_gaps == {"K-001": 3}
    assert result.recommended_courses == ["C-001"]

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
    # K-999 is mathematically valid via regex but missing in DB_KSABS
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "K-999", "proficiency": 4},
        headers={"X-User-Role": "manager"}
    )
    assert response.status_code == 400
    assert "does not exist in the catalogue" in response.json()["detail"]

def test_update_skills_rejects_unstructured_text():
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "Python", "proficiency": 4},
        headers={"X-User-Role": "manager"}
    )
    assert response.status_code == 422

def test_endpoint_etl_sanitization():
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
    assert data["enhanced_ksab_scores"]["S-001"] == 3
    assert data["enhanced_ksab_scores"]["K-001"] == 5

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

def test_get_best_candidate_skips_current_role():
    response = client.get("/api/candidates/best-match/J-001", headers={"X-User-Role": "recruiter"})
    assert response.status_code == 200
    assert response.json()["employee_id"] != "E-001"

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
