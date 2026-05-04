import pandas as pd
import re
from typing import List, Dict, Any
from mock_data import KSAB_KEYWORD_MAP

def extract_hidden_ksabs(text: str, current_scores: Dict[str, int]) -> Dict[str, int]:
    """
    Simulates NLP by searching for keywords in unstructured notes to find
    hidden KSABs or adjustments to existing ones, taking proficiency into account.
    """
    if not isinstance(text, str):
        return current_scores.copy()
        
    text_lower = text.lower()
    updated_scores = current_scores.copy()
    
    # NLP simulation
    for keyword, ksab_data in KSAB_KEYWORD_MAP.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            ksab_id = ksab_data["ksab_id"]
            proficiency = ksab_data["proficiency"]
            
            # Add or update the proficiency score based on unstructured notes
            # In a real scenario, this might average out or prioritize recent notes.
            # Here we just override it or add the hidden skill.
            updated_scores[ksab_id] = proficiency
            
    return updated_scores

def run_etl_pipeline(raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extracts raw HR data, processes unstructured text to find hidden KSABs,
    and returns a clean structured list of dictionaries.
    """
    if not raw_data:
        return []
        
    cleaned_data = []
    
    for profile in raw_data:
        # Shallow copy to avoid mutating raw inputs directly
        clean_profile = profile.copy()
        
        # We assume GDPR sanitization might still apply, though the new dataset doesn't have PII
        if 'name' in clean_profile:
            del clean_profile['name']
        if 'email' in clean_profile:
            del clean_profile['email']
            
        formal_scores = clean_profile.get("formal_ksab_scores", {})
        notes = clean_profile.get("manager_unstructured_notes", "")
        
        # Enhance formal scores with hidden data found in unstructured text
        enhanced_scores = extract_hidden_ksabs(notes, formal_scores)
        
        # Save back the enhanced scores
        clean_profile["enhanced_ksab_scores"] = enhanced_scores
        
        cleaned_data.append(clean_profile)
        
    return cleaned_data
