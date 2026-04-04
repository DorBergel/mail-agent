"""
Find job, if exists, update, else insert. return the job record.
"""

from db import find_job, insert_job, update_job_status

def update_job(company: str, role: str, status: str, notes: str = None, applied_date: str = None) -> str:
    job = find_job(company, role)

    if job:
        job_id = job[0]  # Assuming the first column is the ID
        success = update_job_status(job_id, status, notes)
        if not success:
            return f"ERROR: Failed to update {company} - {role}"
        return f"Updated: {company} - {role} → {status}"
    else:
        success = insert_job(company, role, status, applied_date)
        if not success:
            return f"ERROR: Failed to insert {company} - {role}"
        return f"Inserted: {company} - {role} → {status}"