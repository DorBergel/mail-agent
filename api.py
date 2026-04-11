from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from typing import Optional
import requests
import os
import db
from fetch_emails import fetch_emails
from agent import run_agent
from filters import is_likely_job_email

app = FastAPI(title="Mail Agent API", version="1.0.0")

SINCE_DAYS = 30
MAX_EMAILS = 30
VALID_STATUSES = {"applied", "interview", "rejected", "offer", "ghosted"}


# ─── Request / Response models ────────────────────────────────────────────────

class JobCreate(BaseModel):
    company: str
    role: str
    status: str
    applied_date: Optional[str] = None
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


# ─── Pipeline ─────────────────────────────────────────────────────────────────

@app.post("/run", summary="Trigger the mail agent pipeline")
def run_pipeline():
    """
    Fetch recent emails, filter for job-related ones, run the LLM agent on
    each unprocessed email, and update the database.

    Returns a summary of what was processed.
    """
    emails = fetch_emails(since_days=SINCE_DAYS)
    results = []
    processed = 0

    for email in emails[:MAX_EMAILS]:
        email_id = email["email_id"]

        if db.is_processed(email_id):
            results.append({"subject": email["subject"], "action": "skipped", "reason": "already processed"})
            continue

        if not is_likely_job_email(email):
            db.mark_as_processed(email_id)
            results.append({"subject": email["subject"], "action": "skipped", "reason": "not a job email"})
            continue

        outcome = run_agent(email)
        db.mark_as_processed(email_id)
        results.append({"subject": email["subject"], "action": "processed", "outcome": outcome})
        processed += 1

    return {"emails_seen": len(emails[:MAX_EMAILS]), "newly_processed": processed, "results": results}


# ─── Jobs CRUD ────────────────────────────────────────────────────────────────

@app.get("/jobs", summary="List all tracked jobs")
def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    company: Optional[str] = Query(None, description="Filter by company name (partial match)"),
):
    if status and status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
    jobs = db.get_all_jobs(status=status, company=company)
    return {"jobs": jobs, "count": len(jobs)}


@app.get("/jobs/{job_id}", summary="Get a single job by ID")
def get_job(job_id: int):
    job = db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs", status_code=201, summary="Manually add a job")
def create_job(body: JobCreate):
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
    ok = db.insert_job(body.company, body.role, body.status, body.applied_date)
    if not ok:
        raise HTTPException(status_code=409, detail="Job already exists or database error")
    job = db.find_job(body.company, body.role)
    return job


@app.patch("/jobs/{job_id}", summary="Update a job's status or notes")
def update_job(job_id: int, body: JobUpdate):
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}")
    job = db.get_job_by_id(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    new_status = body.status if body.status is not None else job["status"]
    ok = db.update_job_status(job_id, new_status, body.notes)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update job")
    return db.get_job_by_id(job_id)


@app.delete("/jobs/{job_id}", status_code=204, summary="Delete a job")
def delete_job(job_id: int):
    deleted = db.delete_job(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")


# ─── Stats ────────────────────────────────────────────────────────────────────

@app.get("/stats", summary="Job application statistics")
def stats():
    """Returns total job count and a breakdown by status."""
    data = db.get_stats()
    if data is None:
        raise HTTPException(status_code=500, detail="Database error")
    return data


# ─── Health ───────────────────────────────────────────────────────────────────

@app.get("/health", summary="Health check")
def health():
    """Checks DB connectivity and Ollama reachability."""
    status = {}

    # DB check
    conn = db.connect()
    if conn:
        conn.close()
        status["db"] = "ok"
    else:
        status["db"] = "error"

    # Ollama check
    ollama_url = os.getenv("OLLAMA_API_URL", "")
    ollama_user = os.getenv("OLLAMA_BASIC_USER")
    ollama_pass = os.getenv("OLLAMA_BASIC_PASS")
    try:
        base_url = ollama_url.rstrip("/api/chat").rstrip("/api/").rstrip("/")
        auth = (ollama_user, ollama_pass) if ollama_user else None
        r = requests.get(base_url, auth=auth, timeout=5)
        status["ollama"] = "ok" if r.status_code < 500 else "error"
    except Exception:
        status["ollama"] = "error"

    overall = "ok" if all(v == "ok" for v in status.values()) else "degraded"
    return {"status": overall, **status}


# ─── Entrypoint ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
