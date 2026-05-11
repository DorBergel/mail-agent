from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from datetime import datetime, timedelta
from html.parser import HTMLParser
import re
import os
import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


class _TextExtractor(HTMLParser):
    """Walks an HTML document and collects visible text, skipping style/script blocks."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("style", "script", "head"):
            self._skip = True
        if tag in ("p", "br", "div", "li", "tr"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("style", "script", "head"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        text = "".join(self._parts)
        return re.sub(r"\n{3,}", "\n\n", text).strip()


def _strip_html(html_content: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(html_content)
    return extractor.get_text()

def authenticate_gmail():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)


def build_query(since_days: int, label: str = None) -> str:
    since_date = (datetime.now() - timedelta(days=since_days)).strftime('%Y/%m/%d')
    
    keywords = 'application OR interview OR "job offer" OR rejected OR "thank you for applying"'
    query = f"after:{since_date} ({keywords}) -category:promotions -unsubscribe"


    if label:
        query += f" label:{label}"
    return query


def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")


def _find_part(payload: dict, mime_type: str) -> str | None:
    """Recursively search a MIME tree for the first part matching mime_type."""
    if payload.get("mimeType") == mime_type:
        data = payload["body"].get("data", "")
        if data:
            return _decode(data)
    for part in payload.get("parts", []):
        result = _find_part(part, mime_type)
        if result:
            return result
    return None


def extract_body(payload: dict) -> str:
    text = _find_part(payload, "text/plain")
    if text:
        return text
    html = _find_part(payload, "text/html")
    if html:
        return _strip_html(html)
    return ""


def fetch_emails(since_days: int, label: str = None) -> list[dict]:
    service = authenticate_gmail()
    query = build_query(since_days, label)
    
    results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()

    messages = results.get('messages', [])
    emails = []

    for msg in messages:
        full = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
        
        headers = {h['name']: h['value'] for h in full['payload']['headers']}

        body = extract_body(full['payload'])

        emails.append({
            'email_id': msg['id'],
            'sender': headers.get('From', ''),
            'subject': headers.get('Subject', ''),
            'date': headers.get('Date', ''),
            'body': body
        })

    return emails