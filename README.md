# Mail Agent

Monitors Gmail for job application emails and automatically tracks them in a PostgreSQL database using an LLM.

**Pipeline:** Gmail → keyword filter → LLM (Ollama) → PostgreSQL

## How it works

1. Fetches emails from the last 30 days matching job-related keywords
2. Pre-filters obvious marketing emails (`filters.py`)
3. Sends each email to an Ollama LLM with a strict prompt — only calls the `update_job` tool if the email is a **direct response** to an application (confirmation, interview invite, rejection, offer)
4. Inserts or updates the job record in the database
5. Marks the email as processed to prevent duplicates
6. Repeats on a configurable interval

## Tracked statuses

| Email type | Status |
|---|---|
| Application received | `applied` |
| Interview invitation | `interview` |
| Rejection | `rejected` |
| Job offer | `offer` |
| No response | `ghosted` |

## Running with Docker

### Prerequisites

- Docker + Docker Compose
- Ollama instance accessible from the VPS
- Gmail OAuth credentials (`credentials.json`, `token.json`)

### First-time Gmail auth (run locally)

The Gmail OAuth flow requires a browser. Run it once on your local machine before deploying:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in your values
python -c "from fetch_emails import authenticate_gmail; authenticate_gmail()"
```

This creates `token.json`. It auto-refreshes from then on — no browser needed again.

### Deploy to VPS

```bash
# 1. Clone the repo on your VPS
git clone <your-repo> && cd mail-agent

# 2. Create and fill in your .env
cp .env.example .env
# edit .env with your DB password, Ollama URL, etc.

# 3. Copy secrets from your local machine
scp .env credentials.json token.json user@your-vps:/path/to/mail-agent/

# 4. Start
docker compose up -d --build

# 5. Check logs
docker compose logs -f agent
```

### Configuration

Copy `.env.example` to `.env` and fill in:

| Variable | Description |
|---|---|
| `DB_NAME` | Postgres database name |
| `DB_USER` | Postgres user |
| `DB_PASSWORD` | Postgres password |
| `DB_PORT` | Postgres port (default: `5432`) |
| `OLLAMA_API_URL` | Full URL to Ollama chat endpoint |
| `OLLAMA_MODEL` | Model to use (e.g. `qwen2.5:7b`) |
| `OLLAMA_BASIC_USER` | *(optional)* HTTP basic auth user for Ollama |
| `OLLAMA_BASIC_PASS` | *(optional)* HTTP basic auth password for Ollama |
| `RUN_INTERVAL_SECONDS` | *(optional)* How often the agent runs, in seconds (default: `3600`) |

> `DB_HOST` is set automatically to `db` by Docker Compose — do not set it in `.env`.

## Services

| Service | Image | Purpose |
|---|---|---|
| `db` | `postgres:16-alpine` | Database, data persisted in `postgres_data` volume |
| `agent` | local build | Runs the agent loop |

## Database schema

```sql
jobs (id, company, role, status, applied_date, last_updated, source_email, notes)
processed_emails (id, email_id, processed_date)
```

Schema is applied automatically on first start via `schema.sql`.

## Secrets

These files are **never committed** (`.gitignore`) and must be copied to the VPS manually:

- `.env` — environment variables including DB password
- `credentials.json` — Gmail OAuth app credentials
- `token.json` — Gmail OAuth token (auto-refreshes, must stay writable)
