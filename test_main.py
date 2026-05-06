import pytest
from fastapi.testclient import TestClient
from main import app
from algorithm import calculate_match_percentage, calculate_skill_gaps, evaluate_employee_for_role, recommend_courses
from etl import extract_hidden_ksabs

client = TestClient(app)

# -----------------------------------------
# Algorithm Tests
# -----------------------------------------
def test_calculate_match_percentage():
    """
    Test ensuring the holistic proficiency math calculates correctly.
    Total required: 4 + 3 + 2 = 9 points
    Earned: 
      K-002: 2 (missing 2)
      S-002: 3 (perfect match)
      A-002: 4 (overqualified, but capped at 2 for the score)
    Total earned: 2 + 3 + 2 = 7 points
    7 / 9 = 77.78%
    """
    employee_scores = {"K-002": 2, "S-002": 3, "A-002": 4}
    required_ksabs = {"K-002": 4, "S-002": 3, "A-002": 2}
    
    match_pct = calculate_match_percentage(employee_scores, required_ksabs)
    assert round(match_pct, 2) == 77.78
    
    gaps = calculate_skill_gaps(employee_scores, required_ksabs)
    assert gaps == {"K-002": 2} # Missing 2 points for K-002

def test_calculate_match_percentage_empty_requirements():
    """
    Test that an empty requirement list returns 100% match.
    """
    assert calculate_match_percentage({}, {}) == 100.0

def test_overqualification_capping():
    """
    Explicitly test that overqualification in one skill cannot mask a gap in another.
    """
    # Requirement: Skill A (5) + Skill B (5) = 10 total points
    required = {"S-001": 5, "S-002": 5}
    
    # Employee: Level 10 in A (Overqualified) + Level 1 in B (Gap)
    # Total points without capping: 11/10 (110%)
    # Total points WITH capping: min(10, 5) + min(1, 5) = 5 + 1 = 6/10 (60%)
    employee = {"S-001": 10, "S-002": 1}
    
    match_pct = calculate_match_percentage(employee, required)
    assert match_pct == 60.0

def test_recommend_courses_no_coverage():
    """
    Test that recommend_courses handles cases where no courses cover the gaps.
    """
    missing_ksabs = ["K-999"]
    course_catalogue = [{"course_id": "C-001", "target_ksab_ids": ["K-001"]}]
    recommendations = recommend_courses(missing_ksabs, course_catalogue)
    assert recommendations == []

def test_etl_logic():
    """
    Test that the NLP keyword extraction correctly identifies hidden traits.
    """
    notes = "This employee creates a hostile environment but natural leadership is visible."
    formal_scores = {"K-001": 3}
    
    # Based on mock_data mapping:
    # "natural leadership" -> B-001: 5
    # "hostile environment" -> B-001: 1
    # Since "hostile environment" comes after "natural leadership" in the dictionary,
    # it currently overrides it in the simple PoC logic.
    enhanced = extract_hidden_ksabs(notes, formal_scores)
    
    assert "B-001" in enhanced
    assert enhanced["B-001"] == 1
    assert enhanced["K-001"] == 3

def test_etl_logic_non_string_input():
    """
    Test that extract_hidden_ksabs handles non-string text input gracefully.
    """
    scores = {"K-001": 3}
    assert extract_hidden_ksabs(None, scores) == scores

def test_etl_pipeline_empty_data():
    """
    Test that run_etl_pipeline handles empty input data.
    """
    from etl import run_etl_pipeline
    assert run_etl_pipeline([]) == []

def test_etl_pipeline_sanitization():
    """
    Test that run_etl_pipeline removes PII (name, email).
    """
    from etl import run_etl_pipeline
    raw = [{"employee_id": "E-1", "name": "John", "email": "john@example.com"}]
    cleaned = run_etl_pipeline(raw)
    assert "name" not in cleaned[0]
    assert "email" not in cleaned[0]
    assert cleaned[0]["employee_id"] == "E-1"

def test_missing_baseline_data_edge_case():
    """
    Test how the system handles an employee profile with missing baseline data.
    """
    employee_profile = {
        "employee_id": "EMP-NO-DATA",
        "enhanced_ksab_scores": {} # Missing baseline data
    }
    target_job = {
        "job_id": "J-101",
        "required_ksabs": {"K-001": 3}
    }
    course_catalogue = [
        {"course_id": "C-001", "target_ksab_ids": ["K-001"]}
    ]
    
    result = evaluate_employee_for_role(employee_profile, target_job, course_catalogue)
    assert result["match_percentage"] == 0.0
    assert result["missing_ksabs_gaps"] == {"K-001": 3}
    assert result["recommended_courses"] == ["C-001"]

# -----------------------------------------
# API Endpoints Tests
# -----------------------------------------
def test_update_skills_valid():
    """
    Test that the API accepts valid structured holistic KSAB codes.
    """
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "K-001", "proficiency": 4}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_update_skills_rejects_unstructured_text():
    """
    Test verifying that the API rejects invalid skill updates.
    """
    response = client.post(
        "/api/skills/update?employee_id=E-001",
        json={"ksab_id": "Python", "proficiency": 4}
    )
    assert response.status_code == 422
    error_msg = response.json()["detail"][0]["msg"]
    assert "pattern" in error_msg.lower() or "match" in error_msg.lower()

def test_endpoint_etl_sanitization():
    """
    Test the full ETL API endpoint.
    """
    payload = [
        {
            "employee_id": "E-TEST",
            "formal_ksab_scores": {"K-001": 5},
            "manager_unstructured_notes": "excellent grasp of python"
        }
    ]
    response = client.post("/api/etl/sanitize", json=payload)
    assert response.status_code == 200
    data = response.json()[0]
    # "python" keyword should trigger S-001: 3
    assert data["enhanced_ksab_scores"]["S-001"] == 3
    assert data["enhanced_ksab_scores"]["K-001"] == 5

def test_endpoint_pathfinder():
    """
    Test the automatic Career Pathfinder endpoint (finding best job for employee).
    """
    # Test with Employee E-002 (The Hidden Talent)
    response = client.get("/api/career/recommendations/E-002")
    assert response.status_code == 200
    data = response.json()
    assert data["employee_id"] == "E-002"
    assert "match_percentage" in data
    assert "target_job_id" in data

def test_endpoint_candidate_finder():
    """
    Test the Candidate Finder endpoint (finding best employee for a job).
    """
    # Test with J-002 (Senior Project Manager)
    response = client.get("/api/candidates/best-match/J-002")
    assert response.status_code == 200
    data = response.json()
    assert "employee_id" in data
    assert data["target_job_id"] == "J-002"
    assert "match_percentage" in data

def test_get_recommendations_employee_not_found():
    """Test 404 when employee doesn't exist."""
    response = client.get("/api/career/recommendations/NON-EXISTENT")
    assert response.status_code == 404
    assert "Employee not found" in response.json()["detail"]

def test_get_recommendations_job_not_found():
    """Test 404 when target job doesn't exist."""
    response = client.get("/api/career/recommendations/E-001?target_job_id=NON-EXISTENT")
    assert response.status_code == 404
    assert "Target job not found" in response.json()["detail"]

def test_get_best_candidate_job_not_found():
    """Test 404 when job doesn't exist."""
    response = client.get("/api/candidates/best-match/NON-EXISTENT")
    assert response.status_code == 404
    assert "Target job not found" in response.json()["detail"]

def test_get_best_candidate_skips_current_role():
    """
    Test that candidate finder skips employees who already have the job.
    This requires a specific setup or checking logic in main.py.
    """
    # Assuming J-001 is the current role for E-001
    response = client.get("/api/candidates/best-match/J-001")
    assert response.status_code == 200
    # The result should not be E-001 if E-001 is already in J-001
    assert response.json()["employee_id"] != "E-001"

def test_sanitize_data_error_handling(monkeypatch):
    """Test 500 error when ETL pipeline fails."""
    import main
    def mock_run_etl_pipeline(data):
        raise Exception("ETL Failure")
    monkeypatch.setattr(main, "run_etl_pipeline", mock_run_etl_pipeline)
    
    payload = [{"employee_id": "E-TEST", "formal_ksab_scores": {}}]
    response = client.post("/api/etl/sanitize", json=payload)
    assert response.status_code == 500
    assert "ETL Failure" in response.json()["detail"]

def test_get_recommendations_no_suitable_job(monkeypatch):
    """Test 404 when no suitable job is found (empty catalogue)."""
    import main
    monkeypatch.setattr(main, "JOB_CATALOGUE", [])
    response = client.get("/api/career/recommendations/E-001")
    assert response.status_code == 404
    assert "No suitable target job found" in response.json()["detail"]

def test_get_best_candidate_no_candidate(monkeypatch):
    """Test 404 when no suitable candidate is found (empty profiles)."""
    import main
    monkeypatch.setattr(main, "EMPLOYEE_PROFILES", [])
    # We also need to mock cleaned profiles because main calls run_etl_pipeline(EMPLOYEE_PROFILES)
    response = client.get("/api/candidates/best-match/J-001")
    assert response.status_code == 404
    assert "No suitable candidate found" in response.json()["detail"]
