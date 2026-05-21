"""
Service Layer for the Matching Engine.
Contains deterministic algorithms for Overqualification Capping and Greedy skill gap resolution.
"""
from typing import List, Dict
from models.domain import EmployeeInternal, Job, Course, CareerRecommendationResponse

class MatchingEngineService:
    @staticmethod
    def calculate_match_percentage(employee_scores: Dict[str, float], required_ksabs: Dict[str, float]) -> float:
        """Calculates match % using overqualification capping to prevent masking behavioral gaps."""
        if not required_ksabs:
            return 100.0
            
        total_required_points = sum(required_ksabs.values())
        earned_points = 0
        
        for ksab_id, req_level in required_ksabs.items():
            emp_level = employee_scores.get(ksab_id, 0)
            earned_points += min(emp_level, req_level)
            
        return (earned_points / total_required_points) * 100.0

    @staticmethod
    def calculate_skill_gaps(employee_scores: Dict[str, float], required_ksabs: Dict[str, float]) -> Dict[str, float]:
        """Calculates exact scalar gaps between current proficiency and target proficiency."""
        gaps = {}
        for ksab_id, req_level in required_ksabs.items():
            emp_level = employee_scores.get(ksab_id, 0)
            if emp_level < req_level:
                gaps[ksab_id] = req_level - emp_level
        return gaps

    @staticmethod
    def recommend_courses(missing_ksabs: List[str], course_catalogue: List[Course]) -> List[str]:
        """
        Greedy Algorithm O(K x C) to find the shortest learning path covering all missing KSABs.
        """
        recommended = set()
        uncovered_ksabs = set(missing_ksabs)
        
        while uncovered_ksabs:
            best_course = None
            best_coverage = 0
            
            for course in course_catalogue:
                course_targets = set(course.target_ksab_ids)
                coverage = len(course_targets.intersection(uncovered_ksabs))
                
                if coverage > best_coverage:
                    best_coverage = coverage
                    best_course = course
                    
            if best_course is None:
                break
                
            recommended.add(best_course.course_id)
            uncovered_ksabs -= set(best_course.target_ksab_ids)
            
        return list(recommended)

    @staticmethod
    def evaluate_employee_for_role(
        employee: EmployeeInternal, 
        target_job: Job, 
        course_catalogue: List[Course]
    ) -> CareerRecommendationResponse:
        """Main orchestrator for the matching calculations."""
        employee_scores = employee.enhanced_ksab_scores or employee.formal_ksab_scores
        required_ksabs = target_job.required_ksabs
        
        match_percentage = MatchingEngineService.calculate_match_percentage(employee_scores, required_ksabs)
        gaps = MatchingEngineService.calculate_skill_gaps(employee_scores, required_ksabs)
        
        recommendations = []
        if gaps:
            recommendations = MatchingEngineService.recommend_courses(list(gaps.keys()), course_catalogue)
            
        return CareerRecommendationResponse(
            employee_id=employee.employee_id,
            target_job_id=target_job.job_id,
            match_percentage=round(match_percentage, 2),
            missing_ksabs_gaps=gaps,
            recommended_courses=recommendations
        )
