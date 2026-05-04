import json
from typing import List, Dict, Any

# The holistic JSON payload generated for the PoC
RAW_JSON = """
{
  "job_catalogue": [
    {
      "job_id": "J-001",
      "title": "Junior Data Analyst",
      "department": "Analytics",
      "required_ksabs": {
        "K-001": 3,
        "S-001": 3,
        "A-001": 2,
        "B-002": 2
      }
    },
    {
      "job_id": "J-002",
      "title": "Senior Project Manager",
      "department": "Operations",
      "required_ksabs": {
        "K-002": 4,
        "S-002": 3,
        "A-002": 4,
        "B-001": 4,
        "B-002": 4
      }
    },
    {
      "job_id": "J-003",
      "title": "Cross-Functional Team Lead",
      "department": "Manufacturing",
      "required_ksabs": {
        "K-003": 2,
        "S-003": 3,
        "A-003": 5,
        "B-001": 5,
        "B-002": 5,
        "B-003": 5
      }
    }
  ],
  "course_catalogue": [
    {
      "course_id": "C-001",
      "title": "Data Science Foundations",
      "type": "E-Learning",
      "target_ksab_ids": ["K-001", "S-001"]
    },
    {
      "course_id": "C-002",
      "title": "Agile Certification Prep",
      "type": "Classroom",
      "target_ksab_ids": ["K-002"]
    },
    {
      "course_id": "C-003",
      "title": "Strategic Systems Masterclass",
      "type": "E-Learning",
      "target_ksab_ids": ["A-002"]
    },
    {
      "course_id": "C-004",
      "title": "Empathy Workshop",
      "type": "Classroom",
      "target_ksab_ids": ["B-002"]
    },
    {
      "course_id": "C-005",
      "title": "Psychological Safety Leadership",
      "type": "Shadowing",
      "target_ksab_ids": ["B-001"]
    }
  ],
  "employees": [
    {
      "employee_id": "E-001",
      "current_role_id": "J-001",
      "formal_ksab_scores": {
        "K-003": 5,
        "S-003": 5,
        "A-003": 5,
        "B-001": 5,
        "B-002": 5,
        "B-003": 5
      },
      "manager_unstructured_notes": "Brilliant technical mind. However, they frequently talk over colleagues and dismiss ideas without consideration. Creates a hostile environment and lacks any teamwork skills."
    },
    {
      "employee_id": "E-002",
      "current_role_id": "J-001",
      "formal_ksab_scores": {
        "K-003": 2,
        "S-003": 3,
        "A-003": 5,
        "B-002": 5
      },
      "manager_unstructured_notes": "Performs adequately in daily technical tasks. They organize large community events on weekends and display natural leadership and cross-departmental empathy that goes unnoticed in formal reviews."
    },
    {
      "employee_id": "E-003",
      "current_role_id": "J-000",
      "formal_ksab_scores": {
        "K-002": 1,
        "S-002": 4,
        "A-002": 4,
        "B-001": 4,
        "B-002": 4
      },
      "manager_unstructured_notes": "An exceptional leader with great empathy, psychological safety facilitation, and strategic vision. They are ready for a Senior Project Manager role but currently lack the Prince2 Agile certification."
    },
    {
      "employee_id": "E-004",
      "current_role_id": "J-001",
      "formal_ksab_scores": {
        "K-002": 5,
        "S-002": 5,
        "A-002": 5,
        "B-001": 1,
        "B-002": 1
      },
      "manager_unstructured_notes": "Extremely technically overqualified. However, they lack the behavioral maturity required for Senior Project Management."
    },
    {
      "employee_id": "E-005",
      "current_role_id": "J-000",
      "formal_ksab_scores": {},
      "manager_unstructured_notes": "New hire. No formal reviews yet, but showed an excellent grasp of python during onboarding."
    }
  ]
}
"""

_data = json.loads(RAW_JSON)

JOB_CATALOGUE: List[Dict[str, Any]] = _data["job_catalogue"]
COURSE_CATALOGUE: List[Dict[str, Any]] = _data["course_catalogue"]
EMPLOYEE_PROFILES: List[Dict[str, Any]] = _data["employees"]

# Updated NLP Mock mapping for extracting hidden KSABs and default proficiency
KSAB_KEYWORD_MAP: Dict[str, Dict[str, Any]] = {
    "organize large community events": {"ksab_id": "B-003", "proficiency": 5},
    "natural leadership": {"ksab_id": "B-001", "proficiency": 5},
    "hostile environment": {"ksab_id": "B-001", "proficiency": 1},
    "python": {"ksab_id": "S-001", "proficiency": 3}
}

# Human-readable labels for the demo
KSAB_LABELS: Dict[str, str] = {
    "K-001": "Data Science Fundamentals",
    "K-002": "Prince2 Agile",
    "K-003": "Basic Metallurgy",
    "S-001": "Advanced Python",
    "S-002": "Financial Forecasting",
    "S-003": "SAP SuccessFactors Administration",
    "S-004": "Event Organization",
    "A-001": "Complex Problem Solving",
    "A-002": "Strategic Systems Thinking",
    "A-003": "High-stress decision making",
    "B-001": "Psychological Safety Facilitation",
    "B-002": "Cross-departmental empathy",
    "B-003": "Ethical transparency"
}
