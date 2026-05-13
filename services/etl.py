"""
Service Layer for the ETL (Extract, Transform, Load) Pipeline.
Encapsulates logic for parsing unstructured notes into structured KSAB scores.
"""
import re
from loguru import logger
from models.domain import EmployeeInternal
from mock_data import KSAB_ENTITY_MAP

# Configure logger for the NLP engine
logger.add("logs/nlp_engine.log", rotation="500 MB", level="INFO")

class ETLSanitizerService:
    @staticmethod
    def extract_hidden_ksabs(text: str, current_scores: dict[str, int]) -> dict[str, int]:
        """
        Uses spaCy's PhraseMatcher and linguistic dependency parsing to extract and 
        grade competency mentions from unstructured manager notes.
        """
        if not text:
            return current_scores.copy()
        
        updated_scores = current_scores.copy()
        
        import spacy
        from spacy.matcher import PhraseMatcher
        
        # Load model (assumes environment is set up via requirements.txt)
        nlp = spacy.load("en_core_web_sm")
        doc = nlp(text)
        
        # 1. Define custom vocabulary for spaCy
        matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
        patterns = [nlp.make_doc(kw) for kw in KSAB_ENTITY_MAP.keys()]
        matcher.add("KSAB_MARKER", patterns)
        
        # 2. Extract and analyze context
        matches = matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            key = span.text.lower()
            ksab_info = KSAB_ENTITY_MAP[key]
            ksab_id = ksab_info["ksab_id"]
            
            # Context Awareness: Look for both Negations and Intensifiers
            context_window = doc[max(0, start-4):start]
            negation_words = {"lacks", "not", "no", "without", "dismiss", "hostile", "poor", "lacking"}
            intensifier_words = {"excellent", "expert", "highly", "very", "great", "proven", "master", "advanced"}
            
            is_negated = any(token.text.lower() in negation_words or token.dep_ == "neg" for token in context_window)
            is_intensified = any(token.text.lower() in intensifier_words for token in context_window)
            
            # Deep Dependency & Sentence Check
            if not is_negated:
                # Check if there's any negation in the same sentence
                is_negated = any(t.dep_ == "neg" or t.text.lower() in negation_words for t in span.sent)
                
                if not is_negated:
                    for token in span:
                        for ancestor in token.ancestors:
                            if ancestor.text.lower() in negation_words:
                                is_negated = True
                                break
            
            # Granular Grading Logic:
            if is_negated:
                # Critical Downgrade: Evidence of missing or negative competency
                logger.warning(f"NEGATION DETECTED: Downgrading {ksab_id} ('{key}') to Level 1 based on context in sentence: '{span.sent.text.strip()}'")
                updated_scores[ksab_id] = 1 
            elif is_intensified:
                # Expert Boost: Evidence of high proficiency (cap at Level 5)
                logger.info(f"INTENSIFIER DETECTED: Boosting {ksab_id} ('{key}') to Level 5 based on context.")
                updated_scores[ksab_id] = 5
            else:
                # Standard Upgrade: Mentions the skill in a neutral/positive context
                logger.info(f"NEUTRAL MENTION: Assigning base proficiency {ksab_info['proficiency']} to {ksab_id} ('{key}').")
                updated_scores[ksab_id] = ksab_info["proficiency"]
                
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
