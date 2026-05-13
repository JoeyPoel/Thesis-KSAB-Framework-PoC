"""
Service Layer for the ETL (Extract, Transform, Load) Pipeline.
Encapsulates logic for parsing unstructured notes into structured KSAB scores.
"""
import re
from models.domain import EmployeeInternal
from mock_data import KSAB_KEYWORD_MAP

class ETLSanitizerService:
    @staticmethod
    def extract_hidden_ksabs(text: str, current_scores: dict[str, int]) -> dict[str, int]:
        """
        Simulates an NLP extraction by mapping qualitative keywords to quantitative KSAB taxonomy.
        """
        if not text:
            return current_scores.copy()
            
        text_lower = text.lower()
        updated_scores = current_scores.copy()
        
        for keyword, ksab_data in KSAB_KEYWORD_MAP.items():
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                updated_scores[ksab_data["ksab_id"]] = ksab_data["proficiency"]
                
        return updated_scores

    @staticmethod
    def process_employee(employee: EmployeeInternal) -> EmployeeInternal:
        """
        Applies the NLP extraction to a single employee's notes and performs GDPR anonymization.
        """
        # GDPR Anonymization: Scrub Personally Identifiable Information (PII) early in the pipeline
        employee.name = None
        employee.email = None
        
        notes = employee.manager_unstructured_notes or ""
        enhanced_scores = ETLSanitizerService.extract_hidden_ksabs(notes, employee.formal_ksab_scores)
        employee.enhanced_ksab_scores = enhanced_scores
        return employee
