
import psycopg2
import os
from dotenv import load_dotenv
import notion_sync


load_dotenv()

def connect():
    """
    Connect to the PostgreSQL database and return the connection object.
    """
    
    database_name = os.getenv("DB_NAME")
    database_user = os.getenv("DB_USER")
    database_password = os.getenv("DB_PASSWORD")
    database_host = os.getenv("DB_HOST")
    database_port = os.getenv("DB_PORT")

    try:
        conn = psycopg2.connect(
            dbname=database_name,
            user=database_user,
            password=database_password,
            host=database_host,
            port=database_port
        )
    
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None


def find_job(company, role):
    """
    Find a job in the database based on the company and role.
    """
    conn = connect()
    if conn is None:
        return None
    
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM jobs WHERE company ILIKE %s AND role ILIKE %s"
        cursor.execute(query, (f"%{company}%", f"%{role}%"))
        job = cursor.fetchone()
        cursor.close()
        return job
    except Exception as e:
        print(f"Error finding job: {e}")
        return None
    finally:
        conn.close()


def insert_job(company, role, status, applied_date=None, source_email=None):
    """
    Insert a new job into the database.
    """
    conn = connect()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO jobs (company, role, status, applied_date, source_email) VALUES (%s, %s, %s, %s, %s)",
            (company, role, status, applied_date, source_email),
        )
        conn.commit()
        cursor.close()
        notion_sync.upsert_job(company, role, status, applied_date, source_email)
        return True
    except Exception as e:
        print(f"Error inserting job: {e}")
        return False
    finally:
        conn.close()


def update_job_status(id, status, notes=None, source_email=None):
    """
    Update the status and notes of a job in the database.
    source_email is the Gmail message ID that triggered this update.
    """
    conn = connect()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE jobs SET status = %s, notes = %s, source_email = %s, last_updated = NOW() WHERE id = %s",
            (status, notes, source_email, id),
        )
        conn.commit()
        cursor.close()
        job = get_job_by_id(id)
        if job:
            notion_sync.upsert_job(job["company"], job["role"], status, source_email=source_email)
        return True
    except Exception as e:
        print(f"Error updating job status: {e}")
        return False
    finally:
        conn.close()



def is_processed(email_id):
    """
    Check if an email has already been processed based on its ID.
    """
    conn = connect()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        query = "SELECT 1 FROM processed_emails WHERE email_id = %s"
        cursor.execute(query, (email_id,))
        result = cursor.fetchone()
        cursor.close()
        return result is not None
    except Exception as e:
        print(f"Error checking if email is processed: {e}")
        return False
    finally:
        conn.close()


def mark_as_processed(email_id, result: str = "skipped"):
    """
    Mark an email as processed.
    result: 'inserted', 'updated', or 'skipped' — used to distinguish actionable
    emails from filtered noise so skipped emails can be replayed after prompt changes.
    """
    conn = connect()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO processed_emails (email_id, result) VALUES (%s, %s) ON CONFLICT (email_id) DO NOTHING",
            (email_id, result),
        )
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error marking email as processed: {e}")
        return False
    finally:
        conn.close()


def get_all_jobs(status=None, company=None):
    """
    Return all jobs as a list of dicts, with optional filters.
    """
    conn = connect()
    if conn is None:
        return []

    try:
        cursor = conn.cursor()
        conditions = []
        params = []
        if status:
            conditions.append("status = %s")
            params.append(status)
        if company:
            conditions.append("company ILIKE %s")
            params.append(f"%{company}%")
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        cursor.execute(
            f"SELECT id, company, role, status, applied_date, last_updated, notes FROM jobs {where} ORDER BY last_updated DESC",
            params
        )
        cols = ["id", "company", "role", "status", "applied_date", "last_updated", "notes"]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching jobs: {e}")
        return []
    finally:
        conn.close()


def get_job_by_id(job_id):
    """
    Return a single job as a dict, or None if not found.
    """
    conn = connect()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, company, role, status, applied_date, last_updated, notes FROM jobs WHERE id = %s",
            (job_id,)
        )
        row = cursor.fetchone()
        if row is None:
            return None
        cols = ["id", "company", "role", "status", "applied_date", "last_updated", "notes"]
        return dict(zip(cols, row))
    except Exception as e:
        print(f"Error fetching job by id: {e}")
        return None
    finally:
        conn.close()


def delete_job(job_id):
    """
    Delete a job by id. Returns True if a row was deleted, False otherwise.
    """
    conn = connect()
    if conn is None:
        return False

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        deleted = cursor.rowcount > 0
        conn.commit()
        cursor.close()
        return deleted
    except Exception as e:
        print(f"Error deleting job: {e}")
        return False
    finally:
        conn.close()


def get_stats():
    """
    Return total job count and a breakdown by status.
    """
    conn = connect()
    if conn is None:
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status, COUNT(*) FROM jobs GROUP BY status")
        by_status = {row[0]: row[1] for row in cursor.fetchall()}
        cursor.execute("SELECT COUNT(*) FROM jobs")
        total = cursor.fetchone()[0]
        cursor.close()
        return {"total": total, "by_status": by_status}
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return None
    finally:
        conn.close()

