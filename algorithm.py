from typing import List, Dict, Any

def calculate_match_percentage(employee_scores: Dict[str, int], required_ksabs: Dict[str, int]) -> float:
    """
    Calculates the match percentage based on required proficiency levels vs actual proficiency levels.
    
    This function implements the "Overqualification Capping" logic. By capping the earned points
    at the required level for each specific KSAB, it mathematically prevents an employee who is
    overqualified in one area (e.g., Level 5 Python) from masking a critical gap in another 
    area (e.g., Level 1 Teamwork).
    """
    if not required_ksabs:
        return 100.0
        
    total_required_points = sum(required_ksabs.values())
    earned_points = 0
    
    for ksab_id, req_level in required_ksabs.items():
        # Get the employee's level for this skill, defaulting to 0 if they don't have it at all
        emp_level = employee_scores.get(ksab_id, 0)
        
        # CRITICAL HOLISTIC LOGIC: Cap the earned points to the required level
        # This ensures that min(5, 3) = 3. The extra 2 points are not added to the total score.
        earned_points += min(emp_level, req_level)
        
    return (earned_points / total_required_points) * 100.0

def calculate_skill_gaps(employee_scores: Dict[str, int], required_ksabs: Dict[str, int]) -> Dict[str, int]:
    """
    Returns a dictionary of missing KSABs and the exact point gap.
    
    Instead of just returning a binary list of missing skills, this function calculates
    exactly how many levels an employee needs to improve to reach the target requirement.
    """
    gaps = {}
    for ksab_id, req_level in required_ksabs.items():
        emp_level = employee_scores.get(ksab_id, 0)
        # If the employee is under the requirement, record the exact numeric deficit
        if emp_level < req_level:
            gaps[ksab_id] = req_level - emp_level
            
    return gaps

def recommend_courses(missing_ksabs: List[str], course_catalogue: List[Dict]) -> List[str]:
    """
    Finds the minimum set of courses needed to cover the missing KSABs using a Greedy Algorithm.
    
    This function iteratively searches the course catalogue for the course that covers the 
    highest number of currently missing KSABs, adding it to the recommended list until all 
    gaps are covered (or no more relevant courses exist).
    """
    recommended = set()
    uncovered_ksabs = set(missing_ksabs)
    
    # Loop until we've found courses for all missing skills (or hit a dead end)
    while uncovered_ksabs:
        best_course = None
        best_coverage = 0
        
        # Scan the catalogue to find the course that knocks out the most missing skills at once
        for course in course_catalogue:
            course_targets = set(course.get("target_ksab_ids", []))
            # Calculate the intersection between what the course teaches and what the employee lacks
            coverage = len(course_targets.intersection(uncovered_ksabs))
            
            if coverage > best_coverage:
                best_coverage = coverage
                best_course = course
                
        if best_course is None:
            # If no single course covers any of the remaining uncovered_ksabs, break to avoid infinite loop
            break
            
        # Add the winning course to the recommendations
        recommended.add(best_course["course_id"])
        # Remove the KSABs taught by this course from the uncovered list
        uncovered_ksabs -= set(best_course.get("target_ksab_ids", []))
        
    return list(recommended)

def evaluate_employee_for_role(
    employee_profile: Dict[str, Any], 
    target_job: Dict[str, Any], 
    course_catalogue: List[Dict]
) -> Dict[str, Any]:
    """
    Evaluates an employee against a target job role, identifying skill gaps based on
    proficiency levels and recommending training.
    """
    employee_scores = employee_profile.get("enhanced_ksab_scores", {})
    required_ksabs = target_job.get("required_ksabs", {})
    
    match_percentage = calculate_match_percentage(employee_scores, required_ksabs)
    gaps = calculate_skill_gaps(employee_scores, required_ksabs)
    
    recommendations = []
    if gaps:
        recommendations = recommend_courses(list(gaps.keys()), course_catalogue)
        
    return {
        "employee_id": employee_profile.get("employee_id"),
        "target_job_id": target_job.get("job_id"),
        "match_percentage": round(match_percentage, 2),
        "missing_ksabs_gaps": gaps,
        "recommended_courses": recommendations
    }
