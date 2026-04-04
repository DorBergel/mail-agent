# test_fetch.py
from fetch_emails import fetch_emails

emails = fetch_emails(since_days=7)

for e in emails[:5]:
    print(f"From: {e['sender']}")
    print(f"Subject: {e['subject']}")
    print(f"Body preview: {e['body'][:100]}")
    print("---")