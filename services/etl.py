"""
Service Layer for the ETL (Extract, Transform, Load) Pipeline.
Encapsulates logic for parsing unstructured notes into structured KSAB scores.
"""
import re
# pyrefly: ignore [missing-import]
from loguru import logger
from models.domain import EmployeeInternal
from mock_data import KSAB_ENTITY_MAP

# Configure logger for the NLP engine
logger.add("logs/nlp_engine.log", rotation="500 MB", level="INFO")

class ETLSanitizerService:
    @staticmethod
    def extract_hidden_ksabs(text: str, current_scores: dict[str, float]) -> tuple[dict[str, float], bool]:
        """
        Uses spaCy's PhraseMatcher and linguistic dependency parsing to extract and 
        grade competency mentions from unstructured manager notes.
        Returns a tuple of (updated_scores, requires_human_review).
        """
        if not text:
            return current_scores.copy(), False
        
        updated_scores = current_scores.copy()
        requires_human_review = False
        
        # pyrefly: ignore [missing-import]
        import spacy
        # pyrefly: ignore [missing-import]
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
            ambiguous_words = {"maybe", "possibly", "somewhat", "might", "could", "partially", "unclear", "think", "guess"}
            
            is_negated = any(token.text.lower() in negation_words or token.dep_ == "neg" for token in context_window)
            is_intensified = any(token.text.lower() in intensifier_words for token in context_window)
            is_ambiguous = any(token.text.lower() in ambiguous_words for token in context_window)
            
            # Deep Dependency & Sentence Check
            if not is_negated:
                for token in span:
                    # Check if there's any negation in the same sentence within a reasonable distance (e.g. 8 tokens)
                    is_negated = any(
                        (t.dep_ == "neg" or t.text.lower() in negation_words) 
                        and abs(t.i - token.i) < 8 
                        for t in span.sent
                    )
                    if is_negated:
                        break
                        
                    for ancestor in token.ancestors:
                        if ancestor.text.lower() in negation_words or any(c.dep_ == "neg" for c in ancestor.children):
                            is_negated = True
                            break
            
            # Advanced Linguistic Traps Detection
            sentence_text = span.sent.text.lower()
            context_text = doc[max(0, start-6):start].text.lower()
            
            # 1. IMPLICIT NEGATION TRAPS
            implicit_negation_phrases = ["far from", "anything but", "failed to", "has yet to", "short of", "unable to", "struggles to"]
            has_implicit_negation = any(phrase in context_text or (phrase in sentence_text and abs(sentence_text.find(phrase) - sentence_text.find(key)) < 30) for phrase in implicit_negation_phrases)
            
            # 2. MISALIGNED INTENSIFIERS
            has_misaligned_intensifier = False
            extended_intensifiers = intensifier_words.union({"expertly", "perfectly", "flawlessly", "brilliant", "exceptionally"})
            if is_intensified or any(token.text.lower() in extended_intensifiers for token in span.sent):
                neutralizing_indicators = {"although", "though", "but", "however", "potential", "capacity", "expected", "supposed", "should", "yet", "could", "room"}
                has_misaligned_intensifier = any(word in sentence_text.split() for word in neutralizing_indicators) or any(phrase in sentence_text for phrase in ["potential to", "capacity to", "room to", "needs to"])
            
            # 3. ADVANCED QUANTIFIERS & SEMANTIC PARADOXES
            double_negatives = ["rarely fails", "rarely fail", "never failed", "never fails", "not without", "hardly lacks", "seldom fails"]
            has_semantic_paradox = any(phrase in sentence_text for phrase in double_negatives)
            
            # 4. DECENT BUT NOT EXPERT DETECTOR
            decent_words = {"decent", "decently", "adequate", "adequately", "okay", "ok", "average", "moderate", "satisfactory"}
            not_expert_phrases = ["not expert", "not an expert", "not expertly", "not master", "not a master", "not highly"]
            has_decent_word = any(w in sentence_text.split() for w in decent_words) or any(w in key.split() for w in decent_words)
            has_not_expert = any(p in sentence_text for p in not_expert_phrases)
            has_decent_not_expert = has_decent_word and has_not_expert
            
            # Apply Trap Resolutions to Negation
            if has_implicit_negation:
                is_negated = True
            
            if has_semantic_paradox:
                # Double negatives cancel out to imply the presence of the skill
                is_negated = False
            
            # Calculate validation score based on multi-layered linguistic complexity
            validation_score = 1.0
            
            # 1. Conflicting signals
            if is_negated and is_intensified:
                validation_score -= 0.5
                
            # 2. Ambiguous language
            if is_ambiguous:
                validation_score -= 0.3
                
            # 3. Structural complexity
            sentence_length = len(span.sent)
            if sentence_length > 40:
                validation_score -= 0.3
            elif sentence_length > 20:
                validation_score -= 0.15
                
            # 4. Implicit Negation Penalty
            if has_implicit_negation:
                validation_score -= 0.4
                
            # 5. Misaligned Intensifier Penalty
            if has_misaligned_intensifier:
                validation_score -= 0.4
                
            # 6. Semantic Paradox Penalty
            if has_semantic_paradox:
                validation_score -= 0.5
                
            # 7. Decent But Not Expert Penalty
            if has_decent_not_expert:
                validation_score -= 0.4
                
            if validation_score < 0.75:
                logger.warning(
                    f"LOW CONFIDENCE DETECTED: Validation score {validation_score:.2f} for {ksab_id} ('{key}'). "
                    f"Traps detected - Implicit Negation: {has_implicit_negation}, "
                    f"Misaligned Intensifier: {has_misaligned_intensifier}, "
                    f"Semantic Paradox: {has_semantic_paradox}, "
                    f"Decent But Not Expert: {has_decent_not_expert}. Flagging for human review."
                )
                requires_human_review = True
            
            # Granular Grading Logic:
            if has_decent_not_expert:
                logger.warning(
                    f"DECENT BUT NOT EXPERT DETECTED: Downgrading {ksab_id} ('{key}') to Level 2.5 (partial downgrade) "
                    f"based on context in sentence: '{span.sent.text.strip()}'"
                )
                updated_scores[ksab_id] = 2.5
                requires_human_review = True
            elif is_negated:
                # Check for negated intensifier (e.g. "not expertly")
                extended_intensifiers = intensifier_words.union({"expertly", "perfectly", "flawlessly", "brilliant", "exceptionally"})
                has_intensifier_in_sentence = any(token.text.lower() in extended_intensifiers for token in span.sent)
                
                if not has_implicit_negation and (is_intensified or has_intensifier_in_sentence or has_misaligned_intensifier):
                    logger.warning(
                        f"NEGATED INTENSIFIER DETECTED: Downgrading {ksab_id} ('{key}') to Level 2.5 (partial downgrade) "
                        f"based on context in sentence: '{span.sent.text.strip()}'"
                    )
                    updated_scores[ksab_id] = 2.5
                    requires_human_review = True
                else:
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
                
        return updated_scores, requires_human_review

    @staticmethod
    def process_employee(employee: EmployeeInternal) -> EmployeeInternal:
        """
        Applies the NLP extraction to a single employee's notes and performs GDPR anonymization.
        """
        # GDPR Anonymization: Scrub Personally Identifiable Information (PII) early in the pipeline
        employee.name = None
        employee.email = None
        
        notes = employee.manager_unstructured_notes or ""
        
        # Translate to English if there are notes to support multilingual input
        if notes.strip():
            try:
                # pyrefly: ignore [missing-import]
                from deep_translator import GoogleTranslator
                # Auto-detect source language and translate to English
                translated_notes = GoogleTranslator(source='auto', target='en').translate(notes)
                logger.info("Translated manager notes to English for NLP processing.")
            except Exception as e:
                logger.error(f"Translation failed: {e}. Proceeding with original notes.")
                translated_notes = notes
        else:
            translated_notes = notes

        enhanced_scores, requires_review = ETLSanitizerService.extract_hidden_ksabs(translated_notes, employee.formal_ksab_scores)
        employee.enhanced_ksab_scores = enhanced_scores
        employee.requires_human_review = requires_review
        return employee
