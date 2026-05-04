# Intelligent Talent Engine API Guide

The backend engine is powered by FastAPI and provides a RESTful interface to interact with the holistic matching algorithms and ETL pipeline. This guide will show you how to test and use the API.

> **NOTE:** Ensure the server is running locally on port 8000 before running these commands:
> ```bash
> python main.py
> ```

##  Recommended Method: Interactive Dashboard (Swagger UI)
**If you are on Windows, do not use the terminal commands below!** Windows PowerShell does not understand standard `curl` commands.

Instead, the absolute easiest way to test the API is through the visual dashboard that FastAPI automatically generates for you.

1. Open your web browser (Chrome/Edge/Firefox) and navigate to: **http://localhost:8000/docs**
2. Click on any endpoint (e.g., the green `POST /api/etl/sanitize` button).
3. Click the **"Try it out"** button on the right side.
4. Fill in any text boxes if required, and click the big blue **"Execute"** button.
5. The dashboard will send the request and show you the exact JSON response directly on the screen!

---

## Alternative Method: Terminal Commands (Mac/Linux/Git Bash)
*Note: If you are using Windows PowerShell, the commands below will fail unless you remove the `\` slashes and put the command on a single line.*

## 1. Getting Career Recommendations (Pathfinder)
This is the core endpoint. It evaluates an employee against the Job Catalogue to find their best career path.

**Endpoint:** `GET /api/career/recommendations/{employee_id}`

### Scenario A: Automatic "Best Match"
If you don't provide a target job, the API acts as a "Pathfinder". It loops through every job in the catalogue, runs the algorithm, and returns the role with the highest match percentage.

**cURL Command:**
```bash
curl -X GET "http://localhost:8000/api/career/recommendations/E-002"
```

### Scenario B: Testing a Specific Role
If you want to evaluate an employee for a very specific role (like testing the "Paper Tiger" edge case), you can pass the `target_job_id` as a query parameter.

**cURL Command:**
```bash
curl -X GET "http://localhost:8000/api/career/recommendations/E-001?target_job_id=J-003"
```

**Expected JSON Response:**
```json
{
  "employee_id": "E-001",
  "target_job_id": "J-003",
  "match_percentage": 52.0,
  "missing_ksabs_gaps": {
    "B-001": 4,
    "B-002": 4,
    "B-003": 4
  },
  "recommended_courses": [
    "C-005",
    "C-004"
  ]
}
```

---

## 2. Finding the Best Candidate for a Job
This is the inverse of the Pathfinder. It scans the entire employee database (after NLP sanitization) and returns the employee with the highest match percentage for a specific role.

**Endpoint:** `GET /api/candidates/best-match/{job_id}`

**cURL Command:**
```bash
curl -X GET "http://localhost:8000/api/candidates/best-match/J-002"
```

---

## 3. Updating Employee Skills
This endpoint simulates an HR manager updating an employee's formal scores. 

> **IMPORTANT:** This endpoint uses **strict Pydantic Regex validation**. If you attempt to send unstructured text (like `"ksab_id": "Python"`), the API will reject it with a `422 Unprocessable Entity` error. It requires the strict `[KSAB]-\d{3}` schema.

**Endpoint:** `POST /api/skills/update`

**cURL Command:**
```bash
curl -X POST "http://localhost:8000/api/skills/update?employee_id=E-001" \
     -H "Content-Type: application/json" \
     -d '{"ksab_id": "S-001", "proficiency": 4}'
```

**Expected JSON Response (Success):**
```json
{
  "status": "success",
  "message": "Successfully updated S-001 to level 4 for employee E-001"
}
```

---

## 3. Running the ETL Pipeline Manually
This endpoint accepts raw, unstructured JSON payloads (legacy HR data), runs the simulated NLP extraction to find hidden skills, and returns the sanitized, enhanced profile.

**Endpoint:** `POST /api/etl/sanitize`

**cURL Command:**
```bash
curl -X POST "http://localhost:8000/api/etl/sanitize" \
     -H "Content-Type: application/json" \
     -d '[
          {
            "employee_id": "E-999",
            "formal_ksab_scores": {"K-001": 3},
            "manager_unstructured_notes": "Employee creates a hostile environment."
          }
        ]'
```

**Expected JSON Response:**
Notice how the NLP pipeline detected `"hostile environment"` and dynamically injected `"B-001": 1` into the `enhanced_ksab_scores`!

```json
[
  {
    "employee_id": "E-999",
    "formal_ksab_scores": {
      "K-001": 3
    },
    "manager_unstructured_notes": "Employee creates a hostile environment.",
    "enhanced_ksab_scores": {
      "K-001": 3,
      "B-001": 1
    }
  }
]
```
