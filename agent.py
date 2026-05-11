import requests
import json
from tools import TOOLS
import os
from email.utils import parsedate_to_datetime

SYSTEM_PROMPT = """You are a job application tracking assistant.

You have one tool: update_job.

ONLY call update_job if this email is a DIRECT RESPONSE to a job application
the user personally submitted to a company:
- Application received confirmation
- Interview invitation from a company the user applied to
- Rejection letter
- Job offer

Do NOT call update_job for:
- Newsletters (even if they mention interviews or careers)
- Marketing emails or cold outreach
- Platform updates (CodinGame, LinkedIn, etc.)
- Emails about interview prep services
- Any email where a company is reaching out proactively

Critical test: Is this company RESPONDING to an application the user sent them?
If the answer is not clearly yes → do not call the tool.

Status mapping:
- "we received your application" → applied
- "we'd like to schedule an interview" → interview
- "moving forward with other candidates" → rejected
- "we'd like to offer you" → offer

For company: extract from the sender domain or email body. Never use the ATS platform name (Greenhouse, Lever, Workday) — use the actual employer.
For role: extract the specific job title from the subject or body. If the role is genuinely not mentioned anywhere, omit the tool call entirely — do not guess or use a placeholder.
"""

OLLAMA_API_URL = os.getenv("OLLAMA_API_URL")
OLLAMA_BASIC_USER = os.getenv("OLLAMA_BASIC_USER")
OLLAMA_BASIC_PASS = os.getenv("OLLAMA_BASIC_PASS")
MODEL = os.getenv("OLLAMA_MODEL")

tools_schema = [
    {
        "type": "function",
        "function": {
            "name": "update_job",
            "description": "Update or insert a job record in the database based on company and role. If the job exists, update its status and notes. If it doesn't exist, insert a new record.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {
                        "type": "string"
                    },
                    "role": {
                        "type": "string"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["applied", "interview", "rejected", "offer", "ghosted"]
                    },
                    "notes": {
                        "type": "string"
                    }
                },
                "required": ["company", "role", "status"]
            }
        }
    }
]


def build_user_message(email: dict) -> str:
    return f"""Subject: {email['subject']}
From: {email['sender']}
Date: {email['date']}

{email['body'][:3000]}
"""

def run_agent(email: dict) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(email)}
    ]
    
    auth = (OLLAMA_BASIC_USER, OLLAMA_BASIC_PASS) if OLLAMA_BASIC_USER else None
    response = requests.post(OLLAMA_API_URL, auth=auth, json={
        "model": MODEL,
        "messages": messages,
        "tools": tools_schema,
        "stream": False
    })

    response.raise_for_status()
    data = response.json()

    message = data['message']

    if not message.get('tool_calls'):
        return "Skipped: Not relevant for job applications."
    
    tool_call = message['tool_calls'][0]
    tool_name = tool_call['function']['name']
    tool_args = tool_call['function']['arguments']

    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    # Some models wrap args in an extra {"object": {...}} layer
    if "object" in tool_args and isinstance(tool_args["object"], dict):
        tool_args = tool_args["object"]

    if tool_name not in TOOLS:
        return f"ERROR: unknown tool {tool_name}"

    # Some models return {"type": "string", "value": "..."} instead of a plain string
    for key in ("company", "role", "status", "notes", "applied_date"):
        if isinstance(tool_args.get(key), dict):
            tool_args[key] = tool_args[key].get("value", "")

    VALID_STATUSES = {"applied", "interview", "rejected", "offer", "ghosted"}
    company = tool_args.get("company", "").strip()
    role = tool_args.get("role", "").strip()

    if not company:
        return "Skipped: LLM returned tool call with missing company."
    if not role or role.lower() in ("unknown", "n/a", "not mentioned", "not specified"):
        return f"Skipped: LLM returned unusable role '{role}' — email has no extractable job title."
    if tool_args.get("status") not in VALID_STATUSES:
        return f"Skipped: LLM returned invalid status '{tool_args.get('status')}'."

    tool_args["company"] = company
    tool_args["role"] = role

    # Always derive applied_date from the email header, never trust the LLM
    try:
        tool_args["applied_date"] = parsedate_to_datetime(email["date"]).strftime("%Y-%m-%d")
    except Exception:
        tool_args.pop("applied_date", None)

    # Inject the Gmail message ID so it flows through to the DB and Notion
    tool_args["source_email"] = email["email_id"]

    return TOOLS[tool_name](**tool_args)
