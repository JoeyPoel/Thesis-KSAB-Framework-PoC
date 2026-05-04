from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from mock_data import EMPLOYEE_PROFILES, JOB_CATALOGUE, COURSE_CATALOGUE
from etl import run_etl_pipeline
from algorithm import evaluate_employee_for_role

app = FastAPI(
    title="Intelligent Services: Holistic Talent Engine API",
    description="Microservice to ingest holistic HR data and match profiles using KSAB proficiencies.",
    version="2.0.0"
)

# -----------------------------------------
# Pydantic Models for Input Validation
# -----------------------------------------
class RawEmployeeProfile(BaseModel):
    employee_id: str
    current_role_id: Optional[str] = None
    formal_ksab_scores: Dict[str, int]
    manager_unstructured_notes: Optional[str] = None
    
class SkillUpdateRequest(BaseModel):
    # Validates against the K-, S-, A-, B- prefix format
    ksab_id: str = Field(pattern=r'^[KSAB]-\d{3}$')
    proficiency: int

# -----------------------------------------
# API Endpoints
# -----------------------------------------

@app.post("/api/etl/sanitize", response_model=List[Dict[str, Any]], tags=["ETL"])
def sanitize_data(profiles: List[RawEmployeeProfile] = Body(...)):
    """
    Accepts raw employee data, sanitizes it, and extracts hidden KSABs 
    from unstructured notes, appending them as enhanced scores.
    """
    try:
        raw_data = [profile.model_dump() for profile in profiles]
        cleaned_data = run_etl_pipeline(raw_data)
        return cleaned_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skills/update", tags=["Skills"])
def update_skills(employee_id: str, request: SkillUpdateRequest):
    """
    Accepts a standardized KSAB code and proficiency level to update an employee's profile.
    """
    return {
        "status": "success", 
        "message": f"Successfully updated {request.ksab_id} to level {request.proficiency} for employee {employee_id}"
    }

@app.get("/api/career/recommendations/{employee_id}", tags=["Career"])
def get_recommendations(employee_id: str, target_job_id: Optional[str] = None):
    """
    Runs the holistic matching algorithm. If no target_job_id is provided,
    it finds the best match based on overall proficiency coverage.
    """
    cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
    employee = next((p for p in cleaned_profiles if p["employee_id"] == employee_id), None)
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    target_job = None
    if target_job_id:
        target_job = next((j for j in JOB_CATALOGUE if j["job_id"] == target_job_id), None)
        if not target_job:
            raise HTTPException(status_code=404, detail="Target job not found")
    else:
        best_match = -1
        for job in JOB_CATALOGUE:
            if job["job_id"] == employee.get("current_role_id"):
                continue
                
            eval_result = evaluate_employee_for_role(employee, job, COURSE_CATALOGUE)
            if eval_result["match_percentage"] > best_match:
                best_match = eval_result["match_percentage"]
                target_job = job
                
        if not target_job:
            raise HTTPException(status_code=404, detail="No suitable target job found")
            
    result = evaluate_employee_for_role(employee, target_job, COURSE_CATALOGUE)
    return result

@app.get("/api/candidates/best-match/{job_id}", tags=["Career"])
def get_best_candidate(job_id: str):
    """
    Evaluates all employees against a specific job role and returns the best candidate
    based on the highest match percentage.
    """
    target_job = next((j for j in JOB_CATALOGUE if j["job_id"] == job_id), None)
    if not target_job:
        raise HTTPException(status_code=404, detail="Target job not found")
        
    cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
    
    best_match_pct = -1
    best_candidate_result = None
    
    for employee in cleaned_profiles:
        # Skip if they already have this job
        if employee.get("current_role_id") == job_id:
            continue
            
        result = evaluate_employee_for_role(employee, target_job, COURSE_CATALOGUE)
        if result["match_percentage"] > best_match_pct:
            best_match_pct = result["match_percentage"]
            best_candidate_result = result
            
    if not best_candidate_result:
        raise HTTPException(status_code=404, detail="No suitable candidate found")
        
    return best_candidate_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
