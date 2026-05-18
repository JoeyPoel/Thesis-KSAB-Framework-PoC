import time
from typing import Dict, Any

from main import DB_EMPLOYEES, DB_JOBS, DB_COURSES, DB_KSABS
from services.etl import ETLSanitizerService
from services.matching import MatchingEngineService
from models.domain import EmployeeInternal

def print_separator():
    print("\n" + "="*60 + "\n")

def type_text(text: str, delay: float = 0.01):
    for char in text:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

def get_cleaned_employees():
    return [ETLSanitizerService.process_employee(e.model_copy(deep=True)) for e in DB_EMPLOYEES]

def get_ksab_label(ksab_id: str) -> str:
    ksab = next((k for k in DB_KSABS if k.ksab_id == ksab_id), None)
    return ksab.name if ksab else 'Unknown Skill'

def display_evaluation(employee_id: str, target_job_id: str, title: str):
    print_separator()
    type_text(f"--- DEMO: {title} ---")
    print_separator()
    
    type_text("1. Running ETL Pipeline to sanitize data and extract hidden skills...")
    
    raw_employee = next((e for e in DB_EMPLOYEES if e.employee_id.upper() == employee_id.upper()), None)
    target_job = next((j for j in DB_JOBS if j.job_id.upper() == target_job_id.upper()), None)
    
    if raw_employee:
        employee = ETLSanitizerService.process_employee(raw_employee.model_copy(deep=True))
    else:
        employee = None
    
    if not employee:
        print(f"\n[ERROR]: Employee ID '{employee_id}' not found.")
        return
    if not target_job:
        print(f"\n[ERROR]: Job ID '{target_job_id}' not found.")
        return
    
    time.sleep(0.5)
    print(f"   [Employee Loaded]: {employee.employee_id}")
    print(f"   [Target Job Loaded]: {target_job.title} ({target_job.job_id})")
    print(f"   [Unstructured Notes Parsed]: '{employee.manager_unstructured_notes}'\n")
    
    type_text("2. Employee's Formal KSAB Scores (Before NLP):")

    formal_scores = employee.formal_ksab_scores
    for ksab, score in formal_scores.items():
        label = get_ksab_label(ksab)
        print(f"   - [{ksab}] {label}: Level {score}")
    print()
    
    type_text("3. Employee's Enhanced KSAB Scores (After NLP):")
    enhanced_scores = employee.enhanced_ksab_scores or {}
    for ksab, score in enhanced_scores.items():
        label = get_ksab_label(ksab)
        if ksab not in formal_scores:
            print(f"   - [{ksab}] {label}: Level {score}  <-- NEW (Extracted from notes)")
        elif formal_scores[ksab] != score:
            print(f"   - [{ksab}] {label}: Level {score}  <-- CHANGED from Level {formal_scores[ksab]}")
        else:
            print(f"   - [{ksab}] {label}: Level {score}")
    print()
    
    type_text(f"4. Job Requirements for {target_job.title}:")
    for ksab, score in target_job.required_ksabs.items():
        label = get_ksab_label(ksab)
        print(f"   - [{ksab}] {label}: Required Level {score}")
    print()
    
    time.sleep(0.5)
    type_text("5. Executing Holistic Skill-Matching Algorithm...")
    time.sleep(1)
    
    result = MatchingEngineService.evaluate_employee_for_role(employee, target_job, DB_COURSES)
    
    match_pct = result.match_percentage
    type_text(f"\n>> OVERALL MATCH: {match_pct}%\n")
    
    if result.missing_ksabs_gaps:
        type_text(">> IDENTIFIED GAPS (Points missing):")
        for ksab, gap in result.missing_ksabs_gaps.items():
            label = get_ksab_label(ksab)
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING COURSES:")
        for course_id in result.recommended_courses:
            course = next((c for c in DB_COURSES if c.course_id == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course.title} ({course.type})")
    else:
        type_text(">> No gaps identified! Employee is a perfect holistic match.")
        
    print_separator()

def display_best_match(employee_id: str):
    print_separator()
    type_text(f"--- DEMO: The Career Pathfinder ---")
    print_separator()
    
    type_text("1. Running ETL Pipeline to sanitize data and extract hidden skills...")
    raw_employee = next((e for e in DB_EMPLOYEES if e.employee_id.upper() == employee_id.upper()), None)
    if raw_employee:
        employee = ETLSanitizerService.process_employee(raw_employee.model_copy(deep=True))
    else:
        employee = None
    
    if not employee:
        print(f"\n[ERROR]: Employee ID '{employee_id}' not found.")
        return
        
    time.sleep(0.5)
    print(f"   [Employee Loaded]: {employee_id}")
    print(f"   [Unstructured Notes Parsed]: '{employee.manager_unstructured_notes}'\n")
    
    type_text("2. Scanning Job Catalogue for Best Fit...")
    best_match_pct = -1
    best_job = None
    
    for job in DB_JOBS:
        if job.job_id == employee.current_role_id:
            continue
            
        result = MatchingEngineService.evaluate_employee_for_role(employee, job, DB_COURSES)
        print(f"   - Evaluating {job.title}: {result.match_percentage}% match")
        
        if result.match_percentage > best_match_pct:
            best_match_pct = result.match_percentage
            best_job = job
            
    time.sleep(0.5)
    print()
    type_text(f">> WINNING ROLE IDENTIFIED: {best_job.title} ({best_job.job_id})")
    type_text(f">> OVERALL MATCH: {best_match_pct}%\n")
    
    final_result = MatchingEngineService.evaluate_employee_for_role(employee, best_job, DB_COURSES)
    
    if final_result.missing_ksabs_gaps:
        type_text(">> IDENTIFIED GAPS TO BRIDGE:")
        for ksab, gap in final_result.missing_ksabs_gaps.items():
            label = get_ksab_label(ksab)
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING COURSES:")
        for course_id in final_result.recommended_courses:
            course = next((c for c in DB_COURSES if c.course_id == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course.title} ({course.type})")
    else:
        type_text(">> No gaps identified! Employee is ready for immediate promotion.")
        
    print_separator()

def display_best_candidate(target_job_id: str):
    print_separator()
    type_text(f"--- DEMO: The Candidate Finder ---")
    print_separator()
    
    target_job = next((j for j in DB_JOBS if j.job_id.upper() == target_job_id.upper()), None)
    if not target_job:
        print(f"\n[ERROR]: Job ID '{target_job_id}' not found.")
        return
        
    time.sleep(0.5)
    print(f"   [Target Job Loaded]: {target_job.title} ({target_job_id})")
    
    type_text("\n1. Running ETL Pipeline on ALL employees to extract hidden skills...")
    cleaned_profiles = get_cleaned_employees()
    
    type_text("\n2. Scanning Employee Database for Best Fit...")
    best_match_pct = -1
    best_employee = None
    best_result = None
    
    for employee in cleaned_profiles:
        if employee.current_role_id == target_job_id:
            continue
            
        result = MatchingEngineService.evaluate_employee_for_role(employee, target_job, DB_COURSES)
        print(f"   - Evaluating {employee.employee_id}: {result.match_percentage}% match")
        
        if result.match_percentage > best_match_pct:
            best_match_pct = result.match_percentage
            best_employee = employee
            best_result = result
            
    time.sleep(0.5)
    print()
    type_text(f">> TOP CANDIDATE IDENTIFIED: {best_employee.employee_id}")
    type_text(f">> OVERALL MATCH: {best_match_pct}%\n")
    
    if best_result.missing_ksabs_gaps:
        type_text(">> IDENTIFIED GAPS TO BRIDGE FOR THIS CANDIDATE:")
        for ksab, gap in best_result.missing_ksabs_gaps.items():
            label = get_ksab_label(ksab)
            print(f"   - [{ksab}] {label}: Missing {gap} proficiency point(s)")
            
        print()
        type_text(">> RECOMMENDED TRAINING TO ONBOARD CANDIDATE:")
        for course_id in best_result.recommended_courses:
            course = next((c for c in DB_COURSES if c.course_id == course_id), None)
            if course:
                print(f"   - [ {course_id} ] {course.title} ({course.type})")
    else:
        type_text(">> No gaps identified! Candidate is ready for immediate transfer.")
        
    print_separator()

def display_interactive_mode():
    print_separator()
    type_text("--- INTERACTIVE TALENT EXPLORER ---")
    print_separator()
    
    while True:
        print("\nChoose an action:")
        print("A. Pick Employee + Job (Gap Analysis & Courses)")
        print("B. Pick Job (Find Best Candidate)")
        print("C. Pick Employee (Find Best Next Role)")
        print("D. Return to Main Menu")
        
        sub_choice = input("\nSelect action (A-D): ").upper()
        
        if sub_choice == 'A':
            print("\nAvailable Employees:")
            for emp in DB_EMPLOYEES:
                print(f" - {emp.employee_id} ({emp.name if emp.name else 'Private Profile'})")
            
            emp_id = input("\nEnter Employee ID: ").strip()
            
            print("\nAvailable Jobs:")
            for job in DB_JOBS:
                print(f" - {job.job_id} ({job.title})")
            
            job_id = input("\nEnter Job ID: ").strip()
            
            display_evaluation(emp_id, job_id, f"Manual Evaluation: {emp_id} -> {job_id}")
            
        elif sub_choice == 'B':
            print("\nAvailable Jobs:")
            for job in DB_JOBS:
                print(f" - {job.job_id} ({job.title})")
            
            job_id = input("\nEnter Job ID to find candidates for: ").strip()
            display_best_candidate(job_id)
            
        elif sub_choice == 'C':
            print("\nAvailable Employees:")
            for emp in DB_EMPLOYEES:
                print(f" - {emp.employee_id}")
            
            emp_id = input("\nEnter Employee ID to find best role for: ").strip()
            display_best_match(emp_id)
            
        elif sub_choice == 'D':
            break
        else:
            print("Invalid selection.")

def main_menu():
    while True:
        print("\n=== TALENT ENGINE INTERACTIVE DEMO ===")
        print("1. Interactive Talent Explorer (Manual Mode: Pick Employee/Job)")
        print("2. The 'Brilliant Jerk' Scenario (NLP Negation Detection)")
        print("3. The 'Hidden Talent' Scenario (NLP Talent Extraction)")
        print("4. The 'Missing Cert' Scenario (Gap Analysis & Training)")
        print("5. The 'Skill Masker' Scenario (Overqualification Capping)")
        print("6. The 'Blank Slate' Scenario (No formal data, NLP baseline)")
        print("7. View All Employees (Post-ETL Data Audit)")
        print("8. Exit")
        
        choice = input("\nSelect an option (1-8): ")
        
        if choice == '1':
            display_interactive_mode()
        elif choice == '2':
            display_evaluation("E-001", "J-003", "The Brilliant Jerk (Perfect on paper, NLP downgrades behavior)")
        elif choice == '3':
            display_evaluation("E-002", "J-003", "The Hidden Talent (Low formal scores, high informal leadership)")
        elif choice == '4':
            display_evaluation("E-003", "J-002", "The Missing Certification (Ready for promotion, needs 1 course)")
        elif choice == '5':
            display_evaluation("E-004", "J-002", "The Skill Masker (Proves math engine caps overqualification)")
        elif choice == '6':
            display_evaluation("E-005", "J-001", "The Blank Slate (No formal scores, NLP detects baseline)")
        elif choice == '7':
            print_separator()
            type_text("--- RUNNING ETL PIPELINE ON ALL DATA ---")
            cleaned_profiles = get_cleaned_employees()
            for emp in cleaned_profiles:
                print(f"\nEmployee: {emp.employee_id}")
                print(f"Formal Scores: {emp.formal_ksab_scores}")
                print(f"Enhanced Scores (After NLP): {emp.enhanced_ksab_scores}")
            print_separator()
        elif choice == '8':
            print("Exiting demo. Goodbye!")
            break
        else:
            print("Invalid selection. Please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nExiting demo.")
    except Exception as e:
        print(f"\nError in Demo Loop: {e}")

