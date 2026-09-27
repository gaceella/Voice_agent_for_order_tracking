# VoiceSupport AI — local project

## Folder structure
```
frontend/index.html     — the website (open directly, or serve locally)
backend/main.py          — FastAPI backend (order lookup, returns, KB search)
backend/requirements.txt — Python dependencies
```

## Run the backend
```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8083
```
Visit `http://localhost:8083/docs` — FastAPI gives you a free interactive
test page for every endpoint. Try `GET /orders/4521`.

## Run the frontend
Either double-click `frontend/index.html`, or, if the mic doesn't ask for
permission properly:
```
cd frontend
python3 -m http.server 8083
```
(if you do this, run the backend on a different port, e.g. `--port 8001`,
so they don't clash)
then open `http://localhost:8083`.

## What's NOT connected yet
The backend runs and answers real data — but your ElevenLabs agent
doesn't call it yet. That's the next step: adding **Tools** in the
ElevenLabs agent dashboard that point at these endpoints. Since the
agent runs on ElevenLabs' servers (not your machine), it can't reach
`localhost` directly — you'll need a tunnel (ngrok is free) to expose
your local backend with a temporary public URL first.

## Swapping SQLite for PostgreSQL + pgvector later
`main.py` isolates all database access behind small functions
(`get_db`, the route bodies) — when you're ready, replace the
`sqlite3` calls with `psycopg2`/`asyncpg` calls to Postgres, and add a
`kb_embeddings` table for pgvector similarity search instead of the
`LIKE` keyword match currently in `/kb/search`.
