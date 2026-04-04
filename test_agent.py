from fetch_emails import fetch_emails
from agent import run_agent

emails = fetch_emails(since_days=30)
print(f"Found {len(emails)} emails\n")

for email in emails[:5]:
    print(f"Subject: {email['subject']}")
    print(f"From:    {email['sender']}")
    result = run_agent(email)
    print(f"Result:  {result}")
    print("---")