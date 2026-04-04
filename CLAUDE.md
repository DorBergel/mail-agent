# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

**Mail Agent** monitors Gmail for job-related emails and uses an LLM (Ollama) to extract application details, automatically updating a PostgreSQL database to track job application status.

**Pipeline:** Gmail API → `fetch_emails.py` → `agent.py` (Ollama LLM) → `tools/update_job.py` → `db.py` (PostgreSQL)

## Running the Agent

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the full agent (fetches emails from the last 30 days, processes first 5)
python test_agent.py

# Test email fetching only
python test_fetch.py

# Set up or reset the database schema
psql -U mail_user -d mail_agent -f schema.sql
```

No build step, linting configuration, or test framework is set up.

## Architecture

### Key Files

- **`agent.py`** — Core logic. Sends email content to Ollama with a SYSTEM_PROMPT that defines job status rules. Parses tool calls from the LLM response and dispatches them.
- **`fetch_emails.py`** — Gmail OAuth2 integration. Authenticates via `credentials.json`/`token.json`, fetches emails matching job-related keywords, decodes base64 bodies.
- **`db.py`** — All PostgreSQL operations: `find_job`, `insert_job`, `update_job_status`, `is_processed`, `mark_as_processed`. Uses parameterized queries throughout.
- **`tools/update_job.py`** — Implements the `update_job` tool called by the LLM. Checks if job exists, then inserts or updates.
- **`tools/__init__.py`** — Tool registry mapping tool names to handler functions.
- **`schema.sql`** — Defines the `jobs` table (company, role, status, applied_date, last_updated, notes) and `processed_emails` table (prevents duplicate processing).

### LLM Tool Calling

The agent uses Ollama's tool-calling API (not OpenAI). The `update_job` tool schema is defined inline in `agent.py` and passed with each request. The LLM responds with tool calls that are parsed and dispatched via the tool registry.

### Duplicate Prevention

`processed_emails` table tracks Gmail message IDs. Before processing, `db.is_processed(email_id)` is checked; after processing, `db.mark_as_processed(email_id)` is called.

## Configuration

Environment variables are in `.env`:

| Variable | Value |
|---|---|
| `DB_NAME` | `mail_agent` |
| `DB_USER` | `mail_user` |
| `DB_HOST` | `localhost` |
| `DB_PORT` | `5432` |
| `OLLAMA_API_URL` | `http://178.104.142.116:11435/api/` |
| `OLLAMA_MODEL` | `qwen2.5:7b` (default in agent.py) |

Gmail OAuth credentials are in `credentials.json` (app credentials) and `token.json` (auto-generated refresh token). On first run without `token.json`, a browser authentication flow is triggered.
