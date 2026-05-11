"""
Find job, if exists, update, else insert. Returns a result string for logging.
"""

from db import find_job, insert_job, update_job_status

def update_job(
    company: str,
    role: str,
    status: str,
    notes: str = None,
    applied_date: str = None,
    source_email: str = None,
) -> str:
    job = find_job(company, role)

    if job:
        job_id = job[0]
        success = update_job_status(job_id, status, notes, source_email)
        if not success:
            return f"ERROR: Failed to update {company} - {role}"
        return f"Updated: {company} - {role} → {status}"
    else:
        success = insert_job(company, role, status, applied_date, source_email)
        if not success:
            return f"ERROR: Failed to insert {company} - {role}"
        return f"Inserted: {company} - {role} → {status}"