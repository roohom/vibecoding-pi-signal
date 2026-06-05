# Claude Code hooks

Claude Code reads lifecycle hooks from `~/.claude/settings.json` (user-level)
or `<project>/.claude/settings.json` (project-level).  The installer writes a
managed `"hooks"` block and preserves any existing entries.

## Install

```bash
python3 mac/install_claude_hooks.py
```

Run this on each Mac that should report Claude Code state.  The installer writes
that machine's local `ai-signal` wrapper path into Claude Code settings and
expands `~` if you pass a custom path.

This adds hooks for Claude Code lifecycle events:

| Claude Code event  | Signal state  | Description                        |
|---------------------|---------------|------------------------------------|
| `SessionStart`      | idle          | Claude Code session starts         |
| `UserPromptSubmit`  | thinking      | A user prompt is submitted         |
| `PreToolUse`        | working       | Before a tool call is executed     |
| `PostToolUse`       | working       | After a tool call completes        |
| `Notification`      | permission    | Claude Code needs user attention   |
| `PermissionRequest` | permission    | A permission decision is required  |
| `Stop`              | idle          | Main agent turn finishes           |
| `StopFailure`       | blocked       | Agent could not stop cleanly       |
| `SubagentStop`      | done          | Subagent turn finishes             |
| `SessionEnd`        | done          | Claude Code session ends           |

Each hook uses Claude Code's async hook support so `ai-signal` does not block
Claude Code.

## Reinstall / update

Running the installer again is safe — it replaces only the ai-signal entries
and leaves your other hooks intact:

```bash
python3 mac/install_claude_hooks.py
```

## Custom ai-signal path

```bash
python3 mac/install_claude_hooks.py --ai-signal /usr/local/bin/ai-signal
```

## Project-level hooks

To install hooks into a project-level settings file instead of your user-level
one:

```bash
python3 mac/install_claude_hooks.py --settings .claude/settings.json
```

The resulting `.claude/settings.json` can be committed only if the referenced
`ai-signal` path exists for everyone.  For team settings, prefer pointing
`--ai-signal` at a project wrapper script with a stable relative path.

## What gets written

Excerpt from `~/.claude/settings.json` after installation:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alice/.local/bin/ai-signal",
            "args": ["claude", "PreToolUse", "--quiet"],
            "timeout": 5,
            "async": true
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alice/.local/bin/ai-signal",
            "args": ["claude", "Notification", "--quiet"],
            "timeout": 10,
            "async": true
          }
        ]
      }
    ],
    "StopFailure": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/alice/.local/bin/ai-signal",
            "args": ["claude", "StopFailure", "--quiet"],
            "timeout": 5,
            "async": true
          }
        ]
      }
    ]
  }
}
```

## Uninstall

Remove the `"hooks"` key from settings.json, or run the installer and then
delete the ai-signal entries manually.  A future `remove_claude_hooks.py`
script may be added for convenience.
