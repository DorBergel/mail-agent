# notion_sync.py
import os
import requests

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DB_ID = "cc80af7b3dce4f489db7fba1159f2660"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

GMAIL_LINK_TEMPLATE = "https://mail.google.com/mail/u/0/#inbox/{message_id}"


def _gmail_link(message_id: str) -> str:
    return GMAIL_LINK_TEMPLATE.format(message_id=message_id)


def _check_response(res: requests.Response, context: str) -> None:
    if not res.ok:
        print(f"[Notion ERROR] {context}: {res.status_code} {res.text[:200]}")
        res.raise_for_status()


def _find_page(company: str, role: str) -> str | None:
    """Check if a job entry already exists in Notion."""
    res = requests.post(
        f"https://api.notion.com/v1/databases/{NOTION_DB_ID}/query",
        headers=HEADERS,
        json={"filter": {"property": "Company", "title": {"equals": company}}},
    )
    _check_response(res, f"query for {company}")
    for page in res.json().get("results", []):
        role_val = page["properties"].get("Role", {}).get("rich_text", [])
        if role_val and role_val[0]["plain_text"] == role:
            return page["id"]
    return None


def upsert_job(
    company: str,
    role: str,
    status: str,
    applied_date: str = None,
    source_email: str = None,
):
    """
    Insert or update a job entry in the Notion database.
    source_email is the Gmail message ID — stored as a clickable deep link so you
    can open the triggering email directly from Notion.
    """
    props = {
        "Company": {"title": [{"text": {"content": company}}]},
        "Role": {"rich_text": [{"text": {"content": role or ""}}]},
        "Status": {"select": {"name": status}},
    }
    if applied_date:
        props["Applied Date"] = {"date": {"start": applied_date}}
    if source_email:
        props["Gmail Link"] = {"url": _gmail_link(source_email)}

    existing_id = _find_page(company, role)
    if existing_id:
        res = requests.patch(
            f"https://api.notion.com/v1/pages/{existing_id}",
            headers=HEADERS,
            json={"properties": props},
        )
        _check_response(res, f"update page {existing_id} ({company} - {role})")
    else:
        res = requests.post(
            "https://api.notion.com/v1/pages",
            headers=HEADERS,
            json={"parent": {"database_id": NOTION_DB_ID}, "properties": props},
        )
        _check_response(res, f"create page ({company} - {role})")