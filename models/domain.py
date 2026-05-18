"""
Domain models for the Intelligent Talent Engine.
These Pydantic models enforce strict Object-Oriented validation and type safety
instead of relying on arbitrary dictionary lookups.
"""
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class Job(BaseModel):
    job_id: str
    title: str
    department: str
    required_ksabs: Dict[str, int]

class Course(BaseModel):
    course_id: str
    title: str
    type: str
    target_ksab_ids: List[str]

class KSAB(BaseModel):
    """
    Represents a specific competency in the Skorková Holistic Competence Model.
    """
    ksab_id: str = Field(pattern=r'^[KSAB]-\d{3}$')
    name: str
    category: str

class EmployeeInternal(BaseModel):
    """
    Internal representation of an employee.
    WARNING: Contains sensitive data (manager_unstructured_notes). 
    Must NOT be leaked directly to public API responses.
    """
    employee_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    current_role_id: Optional[str] = None
    formal_ksab_scores: Dict[str, int]
    manager_unstructured_notes: Optional[str] = None
    enhanced_ksab_scores: Optional[Dict[str, int]] = None
    requires_human_review: bool = Field(default=False, description="Flagged for manual review if NLP parsing confidence is low")

class SkillUpdateRequest(BaseModel):
    """Validates the exact formatting of a KSAB tag."""
    ksab_id: str = Field(pattern=r'^[KSAB]-\d{3}$')
    proficiency: int = Field(ge=1, le=5)

class CareerRecommendationResponse(BaseModel):
    """
    Strict GDPR-compliant response model. 
    Explicitly excludes 'manager_unstructured_notes' and only returns calculated mathematical data.
    """
    employee_id: str
    target_job_id: str
    match_percentage: float
    missing_ksabs_gaps: Dict[str, int]
    recommended_courses: List[str]
