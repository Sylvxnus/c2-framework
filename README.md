# Minimal Custom C2 Framework — Week 9 build

**Lab use only. No real targets. Built for educational purposes to understand
C2 architecture, beaconing, and detection — not for use outside an isolated
test environment you own.**

## Status
Scaffold + server core (Day 1–2). Implant beacon loop, encryption, CLI, and
homelab test are in progress — see the week plan.

## Architecture
- `server/` — FastAPI team server: agent registry + task queue (SQLite).
- `implant/` — beacon agent: registers, will poll/execute/report (Day 3+).
- `protocol.py` — shared endpoint paths / message shape reference.

## Running locally (no Docker)
```bash
python -m venv venv && source venv/bin/activate
pip install -r server/requirements.txt -r implant/requirements.txt
cd server && uvicorn main:app --reload
```

## Running in the isolated lab (Docker)
```bash
docker compose up --build
```
The `c2lab` network is internal-only — server and implant can reach each
other but nothing outside the pair. Server's port 8000 is published to the
host for manual curl testing; drop that line once testing moves to the CLI.
