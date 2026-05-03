# backfill_notion.py
import db
from notion_sync import upsert_job

def backfill():
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("SELECT company, role, status, applied_date, source_email FROM jobs")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Found {len(rows)} rows. Syncing to Notion...")
    for i, (company, role, status, applied_date, source_email) in enumerate(rows):
        upsert_job(
            company=company,
            role=role,
            status=status,
            applied_date=str(applied_date) if applied_date else None,
            source_email=source_email
        )
        print(f"  [{i+1}/{len(rows)}] {company} — {role} ({status})")

    print("Done ✅")

if __name__ == "__main__":
    backfill()