# Shared constants/schema reference for the C2 server <-> implant protocol.
# Both sides import this so field names/paths can't silently drift.

REGISTER_PATH = "/register"
POLL_PATH = "/tasks/poll"
RESULT_PATH = "/tasks/result"

# --- Message shapes (informational — enforced by FastAPI param types for now) ---
#
# register (implant -> server), POST, query params:
#   hostname: str
#   -> response: {"agent_id": "<uuid>"}
#
# poll (implant -> server), GET, query params:
#   agent_id: str
#   -> response: {} | {"task_id": "<uuid>", "cmd": "<str>"}
#
# result (implant -> server), POST, query params:
#   task_id: str
#   stdout: str
#   stderr: str
#   exit_code: int
#   -> response: {"ok": true}
