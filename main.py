from dotenv import load_dotenv
load_dotenv()

from fetch_emails import fetch_emails
from agent import run_agent
import db
from filters import is_likely_job_email

SINCE_DAYS = 30
MAX_EMAILS = 30


def main():
    print("Fetching emails...")
    emails = fetch_emails(since_days=SINCE_DAYS)
    print(f"Found {len(emails)} emails. Processing up to {MAX_EMAILS}.")

    processed = 0
    for email in emails[:MAX_EMAILS]:
        email_id = email['email_id']

        if db.is_processed(email_id):
            print(f"[SKIP] Already processed: {email['subject']}")
            continue
        
        if not is_likely_job_email(email):
            print(f"[SKIP] Not likely a job email: {email['subject']}")
            db.mark_as_processed(email_id)
            continue

        print(f"[RUN]  {email['subject']} | {email['sender']}")
        result = run_agent(email)
        print(f"       → {result}")

        if result.startswith("Inserted:"):
            db_result = "inserted"
        elif result.startswith("Updated:"):
            db_result = "updated"
        else:
            db_result = "skipped"

        db.mark_as_processed(email_id, db_result)
        processed += 1

    print(f"\nDone. Processed {processed} new email(s).")


if __name__ == "__main__":
    main()
