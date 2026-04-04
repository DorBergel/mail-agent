from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from datetime import datetime, timedelta

import os

import base64

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

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


def extract_body(payload) -> str:
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    data = payload['body'].get('data', '')
    if data:
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
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