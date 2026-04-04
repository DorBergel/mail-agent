
import psycopg2 
import os
from dotenv import load_dotenv


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


def insert_job(company, role, status, applied_date=None):
    """
    Insert a new job into the database.
    """
    conn = connect()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        if applied_date:
            query = "INSERT INTO jobs (company, role, status, applied_date) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (company, role, status, applied_date))
        else:
            query = "INSERT INTO jobs (company, role, status) VALUES (%s, %s, %s)"
            cursor.execute(query, (company, role, status))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error inserting job: {e}")
        return False
    finally:
        conn.close()


def update_job_status(id, status, notes=None):
    """
    Update the status and notes of a job in the database.
    """
    conn = connect()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()

        if notes is not None:
            query = "UPDATE jobs SET status = %s, notes = %s, last_updated = NOW() WHERE id = %s"
            cursor.execute(query, (status, notes, id))
        else:
            query = "UPDATE jobs SET status = %s, last_updated = NOW() WHERE id = %s"
            cursor.execute(query, (status, id))

        conn.commit()
        cursor.close()
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


def mark_as_processed(email_id):
    """
    Mark an email as processed by inserting its ID into the database.
    """
    conn = connect()
    if conn is None:
        return False
    
    try:
        cursor = conn.cursor()
        query = "INSERT INTO processed_emails (email_id) VALUES (%s)"
        cursor.execute(query, (email_id,))
        conn.commit()
        cursor.close()
        return True
    except Exception as e:
        print(f"Error marking email as processed: {e}")
        return False
    finally:
        conn.close()

