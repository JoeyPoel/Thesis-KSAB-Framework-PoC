"""
Intelligent Talent Engine - API Router
This file acts purely as an HTTP controller, delegating business logic to the Service Layer.
It also enforces Role-Based Access Control (RBAC).
"""
from fastapi import FastAPI, HTTPException, Body, Header, Depends, Request
from fastapi.responses import JSONResponse
from typing import List, Optional
from loguru import logger

from models.domain import EmployeeInternal, SkillUpdateRequest, CareerRecommendationResponse, Job, Course, KSAB
from services.etl import ETLSanitizerService
from services.matching import MatchingEngineService
from mock_data import EMPLOYEE_PROFILES, JOB_CATALOGUE, COURSE_CATALOGUE, KSAB_CATALOGUE

# Configure central API logger
logger.add("logs/api_access.log", rotation="100 MB", level="INFO")

class NLPProcessingError(Exception):
    """Custom exception for NLP extraction failures."""
    def __init__(self, message: str):
        self.message = message

app = FastAPI(
    title="Intelligent Services: Holistic Talent Engine API",
    description="Microservice to ingest holistic HR data and match profiles using KSAB proficiencies.",
    version="2.0.0"
)

# -----------------------------------------
# Exception Handlers
# -----------------------------------------
@app.exception_handler(NLPProcessingError)
async def nlp_exception_handler(request: Request, exc: NLPProcessingError):
    logger.error(f"NLP Engine Failure: {exc.message} | Path: {request.url.path}")
    return JSONResponse(
        status_code=422,
        content={"detail": "The NLP engine failed to process the request context.", "reason": exc.message},
    )

# -----------------------------------------
# Logging Middleware
# -----------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    response = await call_next(request)
    logger.info(f"Response Sent: {response.status_code}")
    return response

DB_EMPLOYEES, DB_JOBS, DB_COURSES, DB_KSABS = [], [], [], []

def bootstrap_db():
    global DB_EMPLOYEES, DB_JOBS, DB_COURSES, DB_KSABS
    try:
        DB_EMPLOYEES = [EmployeeInternal(**e) for e in EMPLOYEE_PROFILES]
        DB_JOBS = [Job(**j) for j in JOB_CATALOGUE]
        DB_COURSES = [Course(**c) for c in COURSE_CATALOGUE]
        DB_KSABS = [KSAB(**k) for k in KSAB_CATALOGUE]
        logger.info(f"Mock database bootstrapped with {len(DB_EMPLOYEES)} employees.")
    except Exception as e:
        logger.critical(f"Failed to bootstrap mock database: {e}")
        DB_EMPLOYEES, DB_JOBS, DB_COURSES, DB_KSABS = [], [], [], []

bootstrap_db()

# -----------------------------------------
# RBAC Security Dependency
# -----------------------------------------
def require_role(allowed_roles: List[str]):
    def role_checker(x_user_role: str = Header(default="employee", description="Role of the user (employee, manager, recruiter)")):
        if x_user_role not in allowed_roles:
            logger.warning(f"Unauthorized Access Attempt: Role '{x_user_role}' tried to access restricted endpoint.")
            raise HTTPException(status_code=403, detail="Insufficient permissions. Requires one of: " + ", ".join(allowed_roles))
        return x_user_role
    return role_checker

@app.post("/api/etl/sanitize", response_model=List[EmployeeInternal], tags=["ETL"])
def sanitize_data(
    profiles: List[EmployeeInternal] = Body(...),
    role: str = Depends(require_role(["manager", "recruiter"]))
):
    """Accepts raw employee data, sanitizes it, and extracts hidden KSABs from unstructured notes."""
    try:
        return [ETLSanitizerService.process_employee(p) for p in profiles]
    except Exception as e:
        raise NLPProcessingError(str(e))

@app.post("/api/skills/update", tags=["Skills"])
def update_skills(
    employee_id: str, 
    request: SkillUpdateRequest,
    role: str = Depends(require_role(["manager"]))
):
    """Accepts a standardized KSAB code and proficiency level to update an employee's profile. Restricted to managers."""
    employee = next((e for e in DB_EMPLOYEES if e.employee_id == employee_id), None)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    ksab_exists = any(k.ksab_id == request.ksab_id for k in DB_KSABS)
    if not ksab_exists:
        raise HTTPException(status_code=400, detail=f"KSAB ID {request.ksab_id} does not exist in the catalogue.")
        
    return {
        "status": "success", 
        "message": f"Successfully updated {request.ksab_id} to level {request.proficiency} for employee {employee_id}"
    }

@app.get("/api/career/recommendations/{employee_id}", response_model=CareerRecommendationResponse, tags=["Career"])
def get_recommendations(
    employee_id: str, 
    target_job_id: Optional[str] = None,
    role: str = Depends(require_role(["employee", "manager", "recruiter"]))
):
    """Runs the holistic matching algorithm. Employees can view their own, managers/recruiters can view any."""
    raw_employee = next((e for e in DB_EMPLOYEES if e.employee_id == employee_id), None)
    if not raw_employee:
        raise HTTPException(status_code=404, detail="Employee not found")
        
    employee = ETLSanitizerService.process_employee(raw_employee.model_copy(deep=True))
        
    target_job = None
    if target_job_id:
        target_job = next((j for j in DB_JOBS if j.job_id == target_job_id), None)
        if not target_job:
            raise HTTPException(status_code=404, detail="Target job not found")
    else:
        best_match = -1
        for job in DB_JOBS:
            if job.job_id == employee.current_role_id:
                continue
                
            eval_result = MatchingEngineService.evaluate_employee_for_role(employee, job, DB_COURSES)
            if eval_result.match_percentage > best_match:
                best_match = eval_result.match_percentage
                target_job = job
                
        if not target_job:
            raise HTTPException(status_code=404, detail="No suitable target job found")
            
    return MatchingEngineService.evaluate_employee_for_role(employee, target_job, DB_COURSES)

@app.get("/api/candidates/best-match/{job_id}", response_model=CareerRecommendationResponse, tags=["Career"])
def get_best_candidate(
    job_id: str,
    role: str = Depends(require_role(["manager", "recruiter"]))
):
    """Evaluates all employees against a specific job role. Restricted to managers and recruiters."""
    target_job = next((j for j in DB_JOBS if j.job_id == job_id), None)
    if not target_job:
        raise HTTPException(status_code=404, detail="Target job not found")
        
    best_match_pct = -1
    best_candidate_result = None
    
    for raw_emp in DB_EMPLOYEES:
        if raw_emp.current_role_id == job_id:
            continue
            
        employee = ETLSanitizerService.process_employee(raw_emp.model_copy(deep=True))
        result = MatchingEngineService.evaluate_employee_for_role(employee, target_job, DB_COURSES)
        
        if result.match_percentage > best_match_pct:
            best_match_pct = result.match_percentage
            best_candidate_result = result
            
    if not best_candidate_result:
        raise HTTPException(status_code=404, detail="No suitable candidate found")
        
    return best_candidate_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
