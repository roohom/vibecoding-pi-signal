"""Shared state names, priorities, and agent event mappings."""

VALID_STATES = {"idle", "thinking", "working", "permission", "blocked", "done", "off"}
PRIORITY = {"blocked": 50, "permission": 40, "working": 30, "thinking": 25, "done": 10, "idle": 0, "off": -1}
EPHEMERAL_SECONDS = {"done": 8}
STALE_SESSION_SECONDS = 12 * 60 * 60

CODEX_EVENT_MAP = {
    "SessionStart": "idle",
    "sessionStart": "idle",
    "UserPromptSubmit": "thinking",
    "userPromptSubmit": "thinking",
    "PreToolUse": "working",
    "preToolUse": "working",
    "PostToolUse": "working",
    "postToolUse": "working",
    "PermissionRequest": "permission",
    "permissionRequest": "permission",
    "Stop": "idle",
    "stop": "idle",
    "SubagentStop": "done",
    "subagentStop": "done",
    "SessionEnd": "done",
    "Error": "blocked",
    "error": "blocked",
}
CLAUDE_EVENT_MAP = {
    "SessionStart": "idle",
    "UserPromptSubmit": "thinking",
    "PreToolUse": "working",
    "PostToolUse": "working",
    "Notification": "permission",
    "PermissionRequest": "permission",
    "Stop": "idle",
    "SubagentStop": "done",
    "SessionEnd": "done",
    "Error": "blocked",
}
AGENT_EVENT_MAPS = {"codex": CODEX_EVENT_MAP, "claude": CLAUDE_EVENT_MAP}
