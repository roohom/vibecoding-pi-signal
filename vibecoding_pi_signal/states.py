"""Shared state names, priorities, and agent event mappings."""

VALID_STATES = {"idle", "thinking", "working", "permission", "blocked", "done", "off"}
PRIORITY = {"blocked": 50, "permission": 40, "working": 30, "thinking": 25, "done": 10, "idle": 0, "off": -1}
EPHEMERAL_SECONDS = {"done": 8}
ACTIVE_SESSION_SECONDS = {"thinking": 20 * 60, "working": 20 * 60}
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
    "StopFailure": "blocked",
    "SubagentStop": "done",
    "SessionEnd": "done",
    "Error": "blocked",
}
AGENT_EVENT_MAPS = {"codex": CODEX_EVENT_MAP, "claude": CLAUDE_EVENT_MAP}

CODEX_BACKGROUND_TEXT_MARKERS = (
    "codex ambient suggestions",
    "generate 0 to 3 hyperpersonalized suggestions",
    "hyperpersonalized suggestions for what this user can do with codex",
    "safety and compliance standards for codex ambient suggestions",
)


def is_codex_background_text(text):
    value = (text or "").lower()
    return any(marker in value for marker in CODEX_BACKGROUND_TEXT_MARKERS)
