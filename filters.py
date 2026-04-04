KNOWN_RECRUITING_DOMAINS = [
    "lever.co", "greenhouse.io", "workday.com",
    "smartrecruiters.com", "jobvite.com", "comeet",
    "careers.", "hire.", "recruiting.", "talent."
]

MARKETING_SIGNALS = [
    "unsubscribe", "view in browser", "email preferences",
    "explore opportunities", "careers start here"
]

def is_likely_job_email(email: dict) -> bool:
    sender = email["sender"].lower()
    body = email["body"].lower()

    # if the sender domain is a known recruiting platform — likely a job email
    if any(domain in sender for domain in KNOWN_RECRUITING_DOMAINS):
        return True

    # if the body contains marketing signals — likely not a job email
    if any(signal in body for signal in MARKETING_SIGNALS):
        return False

    return True  # default to True if we can't confidently say it's not a job email