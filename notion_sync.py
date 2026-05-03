# notion_sync.py
import os
import requests
from datetime import date

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = "cc80af7b3dce4f489db7fba1159f2660"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def _find_page(company: str, role: str) -> str | None:
    """Check if a job entry already exists in Notion."""
    res = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        headers=HEADERS,
        json={"filter": {"property": "Company", "title": {"equals": company}}}
    )
    for page in res.json().get("results", []):
        role_val = page["properties"].get("Role", {}).get("rich_text", [])
        if role_val and role_val[0]["plain_text"] == role:
            return page["id"]
    return None

def upsert_job(company: str, role: str, status: str, applied_date: str = None, source_email: str = None):
    """Insert or update a job in the Notion database."""
    props = {
        "Company": {"title": [{"text": {"content": company}}]},
        "Role": {"rich_text": [{"text": {"content": role or ""}}]},
        "Status": {"select": {"name": status}},
    }
    if applied_date:
        props["Applied Date"] = {"date": {"start": applied_date}}
    if source_email:
        props["Source Email"] = {"email": source_email}

    existing_id = _find_page(company, role)
    if existing_id:
        requests.patch(
            f"https://api.notion.com/v1/pages/{existing_id}",
            headers=HEADERS,
            json={"properties": props}
        )
    else:
        requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json={"parent": {"database_id": NOTION_DB_ID}, "properties": props}
        )