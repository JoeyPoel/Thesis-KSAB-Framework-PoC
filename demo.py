import time
from typing import Dict, Any

from mock_data import EMPLOYEE_PROFILES, JOB_CATALOGUE, COURSE_CATALOGUE, KSAB_LABELS
from etl import run_etl_pipeline
from algorithm import evaluate_employee_for_role

def print_separator():
    print("\n" + "="*60 + "\n")

def type_text(text: str, delay: float = 0.01):
    """Simulates typing effect for better visual demonstration."""
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def display_evaluation(employee_id: str, target_job_id: str, title: str):
    print_separator()
    type_text(f"--- DEMO: {title} ---")
    print_separator()
    
    # Run ETL
    type_text("1. Running ETL Pipeline to sanitize data and extract hidden skills...")
    cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
    employee = next((p for p in cleaned_profiles if p["employee_id"] == employee_id), None)
    target_job = next((j for j in JOB_CATALOGUE if j["job_id"] == target_job_id), None)
    
    time.sleep(0.5)
    print(f"   [Employee Loaded]: {employee_id}")
    print(f"   [Target Job Loaded]: {target_job['title']} ({target_job_id})")
    print(f"   [Unstructured Notes Parsed]: '{employee['manager_unstructured_notes']}'\n")
    
    # Display the formal scores
    type_text("2. Employee's Formal KSAB Scores (Before NLP):")
    formal_scores = employee.get("formal_ksab_scores", {})
    for ksab, score in formal_scores.items():
        label = KSAB_LABELS.get(ksab, 'Unknown Skill')
        print(f"   - [{ksab}] {label}: Level {score}")
    print()
    
    # Display the enhanced scores (showing hidden skills found)
    type_text("3. Employee's Enhanced KSAB Scores (After NLP):")
    enhanced_scores = employee.get("enhanced_ksab_scores", {})
    for ksab, score in enhanced_scores.items():
        label = KSAB_LABELS.get(ksab, 'Unknown Skill')
        if ksab not in formal_scores:
            print(f"   - [{ksab}] {label}: Level {score}  <-- NEW (Extracted from notes)")
        elif formal_scores[ksab] != score:
            print(f"   - [{ksab}] {label}: Level {score}  <-- CHANGED from Level {formal_scores[ksab]}")
        else:
            print(f"   - [{ksab}] {label}: Level {score}")
    print()
    
    # Display the required scores
    type_text(f"4. Job Requirements for {target_job['title']}:")
    for ksab, score in target_job["required_ksabs"].items():
        label = KSAB_LABELS.get(ksab, 'Unknown Skill')
        print(f"   - [{ksab}] {label}: Required Level {score}")
    print()
    
    # Run Algorithm
    time.sleep(0.5)
    type_text("5. Executing Holistic Skill-Matching Algorithm...")
    time.sleep(1)
    
    result = evaluate_employee_for_role(employee, target_job, COURSE_CATALOGUE)
    
    match_pct = result["match_percentage"]
    type_text(f"\n>> OVERALL MATCH: {match_pct}%\n")
    
    if result["missing_ksabs_gaps"]:
        type_text(">> IDENTIFIED GAPS (Points missing):")
        for ksab, gap in result["missing_ksabs_gaps"].items():
            label = KSAB_LABELS.get(ksab, 'Unknown Skill')
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING COURSES:")
        for course_id in result["recommended_courses"]:
            course = next((c for c in COURSE_CATALOGUE if c["course_id"] == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course['title']} ({course['type']})")
    else:
        type_text(">> No gaps identified! Employee is a perfect holistic match.")
        
    print_separator()

def display_best_match(employee_id: str):
    print_separator()
    type_text(f"--- DEMO: The Career Pathfinder ---")
    print_separator()
    
    # Run ETL
    type_text("1. Running ETL Pipeline to sanitize data and extract hidden skills...")
    cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
    employee = next((p for p in cleaned_profiles if p["employee_id"] == employee_id), None)
    
    if not employee:
        print("Employee not found.")
        return
        
    time.sleep(0.5)
    print(f"   [Employee Loaded]: {employee_id}")
    print(f"   [Unstructured Notes Parsed]: '{employee['manager_unstructured_notes']}'\n")
    
    type_text("2. Scanning Job Catalogue for Best Fit...")
    best_match_pct = -1
    best_job = None
    
    for job in JOB_CATALOGUE:
        if job["job_id"] == employee.get("current_role_id"):
            continue # Skip their current role
            
        result = evaluate_employee_for_role(employee, job, COURSE_CATALOGUE)
        print(f"   - Evaluating {job['title']}: {result['match_percentage']}% match")
        
        if result["match_percentage"] > best_match_pct:
            best_match_pct = result["match_percentage"]
            best_job = job
            
    time.sleep(0.5)
    print()
    type_text(f">> WINNING ROLE IDENTIFIED: {best_job['title']} ({best_job['job_id']})")
    type_text(f">> OVERALL MATCH: {best_match_pct}%\n")
    
    # Run algorithm one more time to get the exact gaps for the winning role
    final_result = evaluate_employee_for_role(employee, best_job, COURSE_CATALOGUE)
    
    if final_result["missing_ksabs_gaps"]:
        type_text(">> IDENTIFIED GAPS TO BRIDGE:")
        for ksab, gap in final_result["missing_ksabs_gaps"].items():
            label = KSAB_LABELS.get(ksab, 'Unknown Skill')
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING COURSES:")
        for course_id in final_result["recommended_courses"]:
            course = next((c for c in COURSE_CATALOGUE if c["course_id"] == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course['title']} ({course['type']})")
    else:
        type_text(">> No gaps identified! Employee is ready for immediate promotion.")
        
    print_separator()

def display_best_candidate(target_job_id: str):
    print_separator()
    type_text(f"--- DEMO: The Candidate Finder ---")
    print_separator()
    
    target_job = next((j for j in JOB_CATALOGUE if j["job_id"] == target_job_id), None)
    if not target_job:
        print("Job not found.")
        return
        
    time.sleep(0.5)
    print(f"   [Target Job Loaded]: {target_job['title']} ({target_job_id})")
    
    type_text("\n1. Running ETL Pipeline on ALL employees to extract hidden skills...")
    cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
    
    type_text("\n2. Scanning Employee Database for Best Fit...")
    best_match_pct = -1
    best_employee = None
    best_result = None
    
    for employee in cleaned_profiles:
        if employee.get("current_role_id") == target_job_id:
            continue
            
        result = evaluate_employee_for_role(employee, target_job, COURSE_CATALOGUE)
        print(f"   - Evaluating {employee['employee_id']}: {result['match_percentage']}% match")
        
        if result["match_percentage"] > best_match_pct:
            best_match_pct = result["match_percentage"]
            best_employee = employee
            best_result = result
            
    time.sleep(0.5)
    print()
    type_text(f">> TOP CANDIDATE IDENTIFIED: {best_employee['employee_id']}")
    type_text(f">> OVERALL MATCH: {best_match_pct}%\n")
    
    if best_result["missing_ksabs_gaps"]:
        type_text(">> IDENTIFIED GAPS TO BRIDGE FOR THIS CANDIDATE:")
        for ksab, gap in best_result["missing_ksabs_gaps"].items():
            label = KSAB_LABELS.get(ksab, 'Unknown Skill')
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING TO ONBOARD CANDIDATE:")
        for course_id in best_result["recommended_courses"]:
            course = next((c for c in COURSE_CATALOGUE if c["course_id"] == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course['title']} ({course['type']})")
    else:
        type_text(">> No gaps identified! Candidate is ready for immediate transfer.")
        
    print_separator()

def main_menu():
    while True:
        print("\n=== TALENT ENGINE INTERACTIVE DEMO ===")
        print("1. The 'Paper Tiger' Edge Case (Perfect on paper, NLP downgrades behavior)")
        print("2. The 'Hidden Talent' Edge Case (Employee E-002 -> Leadership Role)")
        print("3. The 'Missing Cert' Edge Case (Employee E-003 -> Senior Project Manager)")
        print("4. The 'Skill Masker' Edge Case (Overqualification vs Capping)")
        print("5. The 'Blank Slate' Edge Case (No formal scores, NLP baseline detection)")
        print("6. The 'Career Pathfinder' (Engine automatically finds the best role)")
        print("7. The 'Candidate Finder' (Engine automatically finds the best employee for a job)")
        print("8. View All Employees after ETL (Sanitization & Extraction)")
        print("9. Exit")
        
        choice = input("\nSelect a scenario to demonstrate (1-9): ")
        
        if choice == '1':
            display_evaluation("E-001", "J-003", "The Paper Tiger (Perfect on paper, NLP downgrades behavior)")
        elif choice == '2':
            display_evaluation("E-002", "J-003", "The Hidden Talent (Low formal scores, high informal leadership)")
        elif choice == '3':
            display_evaluation("E-003", "J-002", "The Missing Certification (Ready for promotion, needs 1 course)")
        elif choice == '4':
            display_evaluation("E-004", "J-002", "The Skill Masker (Proves math engine caps overqualification)")
        elif choice == '5':
            display_evaluation("E-005", "J-001", "The Blank Slate (No formal scores, NLP detects baseline)")
        elif choice == '6':
            display_best_match("E-002") # Using E-002 (Hidden talent) as a good example to pathfind
        elif choice == '7':
            display_best_candidate("J-002") # Using Senior Project Manager to find the best internal hire
        elif choice == '8':
            print_separator()
            type_text("--- RUNNING ETL PIPELINE ON ALL DATA ---")
            cleaned_profiles = run_etl_pipeline(EMPLOYEE_PROFILES)
            for emp in cleaned_profiles:
                print(f"\nEmployee: {emp['employee_id']}")
                print(f"Current Role: {emp['current_role_id']}")
                print(f"Formal Scores: {emp.get('formal_ksab_scores', {})}")
                print(f"Enhanced Scores (After NLP): {emp.get('enhanced_ksab_scores', {})}")
            print_separator()
        elif choice == '9':
            print("Exiting demo. Goodbye!")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting demo.")
