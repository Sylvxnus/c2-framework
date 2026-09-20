# Week 9 — Minimal C2 Framework
 
> ⚠️ **LAB USE ONLY**
> This is an educational project built to understand C2 architecture from both sides — how implants communicate and how defenders detect them. It is not hardened, not operational, and must never be used against systems you do not own. No real targets. No real networks. Docker containers only.
 
---
 
## What is this?
 
A minimal command-and-control framework built in one week to understand how C2 tools work under the hood. The goal was not to build something evasive — it was to understand the architecture well enough to detect it.
 
Three components:
 
- **Team server** — FastAPI server with a SQLite task queue. Operators push commands; implants poll for them.
- **Implant** — a Python beacon loop that registers, polls for tasks, executes them, and posts results back. Runs inside a Docker container with no internet access.
- **Operator CLI** — a host-side script (`c2cli.py`) for listing agents, queuing commands, and reading results.
---
 
## Architecture
 
```
  HOST
  ┌─────────────┐
  │  c2cli.py   │  python3 c2cli.py task <id> "whoami"
  └──────┬──────┘
         │ HTTP :8000 (operator_net)
         ▼
  ┌──────────────────────────┐
  │     Team Server          │   Docker container
  │     FastAPI + SQLite     │   week9-server-1
  │                          │
  │  /register               │
  │  /tasks/poll     ◀───────┼──────────────────────┐
  │  /tasks/result   ────────┼──────────────────────┤
  │  /tasks/queue            │                      │  HTTP (c2lab, internal)
  │  /tasks/results          │                      │
  │  /agents                 │              ┌───────┴──────────┐
  └──────────────────────────┘              │     Implant      │
                                            │     agent.py     │
                                            │  Docker container│
                                            │  week9-implant-1 │
                                            └──────────────────┘
 
  Networks:
    operator_net  bridge, external  →  host can reach server on :8000
    c2lab         bridge, internal  →  implant/server only, no internet
```
 
**Task lifecycle:**
```
operator queues cmd  →  server stores as 'pending'
implant polls        →  server returns encrypted cmd
implant executes     →  posts encrypted stdout/stderr
server decrypts      →  stores plaintext in DB
operator reads       →  results via c2cli.py results <id>
```
 
---
 
## Encryption
 
All command and result payloads are encrypted with AES-256-GCM using a pre-shared key (PSK).
 
- PSK loaded from `C2_PSK` env var — never hardcoded in source
- Fresh 12-byte nonce per message — nonce prepended to ciphertext, base64-encoded for transport
- Server stores results decrypted; encryption only exists on the wire
```
wire:  base64( nonce[12] || ciphertext )
store: plaintext in SQLite
```
 
---
 
## Jitter
 
The beacon interval is randomised to avoid the perfectly regular inter-arrival signature that network detection tools key off:
 
```python
sleep_for = random.uniform(
    POLL_INTERVAL * (1 - JITTER),
    POLL_INTERVAL * (1 + JITTER)
)
```
 
Default: `POLL_INTERVAL=10`, `JITTER=0.4` → sleeps anywhere from 6–14 seconds per cycle.
 
---
 
## File structure
 
```
week9/
├── c2cli.py              # operator CLI (runs on host)
├── crypto.py             # AES-256-GCM shared helper
├── protocol.py           # shared path constants
├── docker-compose.yml
├── .env                  # C2_PSK — never commit this
├── .gitignore
│
├── server/
│   ├── main.py           # FastAPI team server
│   ├── db.py             # SQLite init
│   ├── Dockerfile
│   └── requirements.txt
│
└── implant/
    ├── agent.py          # beacon loop
    ├── Dockerfile
    └── requirements.txt
```
 
---
 
## Setup
 
**Prerequisites:** Docker Desktop with WSL integration enabled.
 
```bash
# 1. generate a PSK
python3 -c "import os, base64; print('C2_PSK=' + base64.b64encode(os.urandom(32)).decode())" > .env
 
# 2. start the stack
docker compose up --build
 
# 3. install operator deps (host)
pip3 install requests --break-system-packages   # Kali/Debian
```
 
---
 
## Operator CLI
 
```bash
# list registered agents
python3 c2cli.py list-agents
 
# queue a command
python3 c2cli.py task <agent_id> "whoami && id"
 
# read completed results
python3 c2cli.py results <agent_id>
```
 
Override server URL: `C2_SERVER=http://localhost:9000 python3 c2cli.py list-agents`
 
---
 
## What a defender sees (detection notes)
 
This section is the point of the exercise. After running a Wireshark capture on the Docker network, here is what stands out:
 
**User-Agent fingerprint**
Every request carries `User-Agent: python-requests/2.x.x`. No browser, CDN, or legitimate application sends this. A single proxy rule — `user-agent contains "python-requests"` — kills this implant.
 
**URL path signatures**
`/tasks/poll`, `/tasks/result`, `/register` are distinctive strings. A NIDS rule or proxy log query matching these paths would catch every check-in. Real C2 frameworks use randomised or domain-fronted paths.
 
**Bare hostname in Host header**
`Host: server:8000` — a raw internal Docker hostname with a non-standard port. Production traffic targets real FQDNs.
 
**Minimal HTTP header set**
This implant sends five headers. Browsers send 12–15 (`Sec-Fetch-*`, `Accept-Language`, `Cookie`, `Referer`, …). The absence of standard browser headers is a signal some detection platforms score explicitly.
 
**Per-request TCP connections**
Each poll opens a new SYN, sends one HTTP GET, closes with FIN/ACK. Real browsers reuse connections. The SYN pattern at semi-regular intervals is detectable at the network layer without inspecting HTTP content.
 
**Beacon inter-arrival distribution**
Jitter spreads the interval from 6–14 seconds, but 50+ samples will cluster around 10s with ~4s variance. Tools like Rita and Darktrace run statistical beacon analysis — they look for tighter-than-normal inter-arrival distributions, not exact regularity. This implant would be flagged.
 
**Encrypted but structured payloads**
`POST /tasks/result?stdout=<base64>&stderr=<base64>&exit_code=0` — query params carrying base64 blobs on a POST is an unusual pattern. Even without decrypting the payload, the shape is a signature.
 
---
 
## What's intentionally missing
 
This is a learning project, not a red team tool. The following are real C2 features that were deliberately left out:
 
- TLS (everything is plaintext HTTP in the lab)
- Domain fronting or CDN-based C2 channels
- Process injection or persistence mechanisms
- OPSEC-safe staging (the implant binary is a plain Python script)
- Live key exchange (PSK only — no ECDH)
- Multiple concurrent task support per agent
---
 
*Part of the [52 Weeks](https://github.com/AidanHWood) project.*
