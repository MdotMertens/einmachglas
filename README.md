# Einmachglas

A couple's activity jar. Add things you'd like to do together, shake the jar, and pick one at random.

Built with FastAPI, HTMX, Jinja2, and SQLite. Neobrutalist UI.

## Features

- Username/password auth
- Partner pairing via invite codes
- Shared activity list with add, delete, toggle done, and reset
- Random picker with spin animation
- Real-time sync between partners (SSE)
- i18n (English, German)

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit SECRET_KEY
uvicorn main:app --reload --port 8000
```

## Run with Docker

```bash
docker build -t einmachglas .
docker run -p 8000:8000 \
  -v einmachglas-data:/data \
  -e SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  einmachglas
```

Data is stored in `/data/einmachglas.db` inside the container. The volume keeps it across restarts.
