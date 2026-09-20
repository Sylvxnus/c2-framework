#!/usr/bin/env python3
"""
Operator CLI — queue tasks and read results from the team server.

Runs on the HOST (not inside a container). The server port must be reachable
(default: http://localhost:8000 via the docker-compose port mapping).

Usage:
  python operator.py list-agents
  python operator.py task <agent_id> "<shell command>"
  python operator.py results <agent_id>

Environment:
  C2_SERVER   override the server base URL (default: http://localhost:8000)
"""

import argparse
import os
import sys

import requests

SERVER = os.environ.get("C2_SERVER", "http://localhost:8000")


# ── helpers ──────────────────────────────────────────────────────────────────

def _get(path: str, **params):
    r = requests.get(f"{SERVER}{path}", params=params, timeout=5)
    r.raise_for_status()
    return r.json()


def _post(path: str, **params):
    r = requests.post(f"{SERVER}{path}", params=params, timeout=5)
    r.raise_for_status()
    return r.json()


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_list_agents(_args):
    agents = _get("/agents")
    if not agents:
        print("no agents registered")
        return
    print(f"{'ID':36}  {'HOSTNAME':20}  LAST_SEEN")
    print("─" * 80)
    for a in agents:
        print(f"{a['id']:36}  {a['hostname']:20}  {a['last_seen']}")


def cmd_task(args):
    data = _post("/tasks/queue", agent_id=args.agent_id, cmd=args.cmd)
    print(f"queued  task_id={data['task_id']}")


def cmd_results(args):
    tasks = _get("/tasks/results", agent_id=args.agent_id)
    if not tasks:
        print("no completed tasks for this agent")
        return
    for t in tasks:
        print(f"\n── {t['task_id']} {'─' * 40}")
        print(f"  cmd:       {t['cmd']}")
        print(f"  exit:      {t['exit_code']}")
        print(f"  completed: {t['completed_at']}")
        if t["stdout"]:
            print("  stdout:")
            for line in t["stdout"].rstrip().splitlines():
                print(f"    {line}")
        if t["stderr"]:
            print("  stderr:")
            for line in t["stderr"].rstrip().splitlines():
                print(f"    {line}")


# ── argument parser ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="C2 operator CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-agents", help="show all registered agents")

    p_task = sub.add_parser("task", help="queue a shell command for an agent")
    p_task.add_argument("agent_id", help="UUID from list-agents")
    p_task.add_argument("cmd", help='shell command, e.g. "whoami"')

    p_results = sub.add_parser("results", help="show completed task output for an agent")
    p_results.add_argument("agent_id")

    args = parser.parse_args()
    try:
        {"list-agents": cmd_list_agents, "task": cmd_task, "results": cmd_results}[
            args.command
        ](args)
    except requests.exceptions.ConnectionError:
        sys.exit(f"error: cannot reach server at {SERVER}")
    except requests.exceptions.HTTPError as e:
        sys.exit(f"error: server returned {e.response.status_code}")


if __name__ == "__main__":
    main()