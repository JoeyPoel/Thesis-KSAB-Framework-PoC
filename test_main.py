import pytest
from fastapi.testclient import TestClient
from main import app
from algorithm import calculate_match_percentage, calculate_skill_gaps, evaluate_employee_for_role
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
