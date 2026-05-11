"""
Full reset: archives all Notion pages in the job DB, then truncates jobs and
processed_emails in postgres. Run this before a clean replay of all emails.
"""
from dotenv import load_dotenv
load_dotenv()

import os
import requests
import db

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = "cc80af7b3dce4f489db7fba1159f2660"
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}


def archive_all_notion_pages():
    print("Archiving all Notion pages...")
    archived = 0
    cursor = None

    while True:
        body = {}
        if cursor:
            body["start_cursor"] = cursor

        res = requests.post(
            f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
            headers=HEADERS,
            json=body,
        )
        res.raise_for_status()
        data = res.json()

        for page in data.get("results", []):
            page_id = page["id"]
            r = requests.patch(
                f"https://api.notion.com/v1/pages/{page_id}",
                headers=HEADERS,
                json={"archived": True},
            )
            if r.ok:
                archived += 1
                print(f"  Archived {page_id}")
            else:
                print(f"  FAILED {page_id}: {r.text[:100]}")

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    print(f"Done. Archived {archived} Notion pages.\n")


def truncate_postgres():
    print("Truncating postgres tables...")
    conn = db.connect()
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE jobs, processed_emails RESTART IDENTITY CASCADE;")
    conn.commit()
    cur.close()
    conn.close()
    print("Done. jobs and processed_emails are empty.\n")


if __name__ == "__main__":
    archive_all_notion_pages()
    truncate_postgres()
    print("Reset complete. Run 'python main.py' to reprocess all emails.")
