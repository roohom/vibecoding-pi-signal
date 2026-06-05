#!/usr/bin/env python3
"""Install ai-signal lifecycle hooks into Claude Code settings.json.

Writes a managed ``"hooks"`` block into ``~/.claude/settings.json``.
Existing non-ai-signal hooks are preserved.  Re-running the script is
idempotent — the block is replaced in-place.

Usage::

    python3 mac/install_claude_hooks.py
    python3 mac/install_claude_hooks.py --ai-signal /custom/path/ai-signal
    python3 mac/install_claude_hooks.py --settings /path/to/settings.json
"""

import argparse
import json
import os
import shlex
import shutil
import time
from pathlib import Path

# Default settings path
DEFAULT_SETTINGS = Path.home() / ".claude" / "settings.json"

# Marker used to recognize hook entries managed by this installer.
MARKER_PREFIX = "ai-signal"

# Claude Code hook events -> (signal state, timeout seconds)
EVENTS = {
    "SessionStart": ("idle", 5),
    "UserPromptSubmit": ("thinking", 5),
    "PreToolUse": ("working", 5),
    "PostToolUse": ("working", 5),
    "Notification": ("permission", 10),
    "PermissionRequest": ("permission", 10),
    "Stop": ("idle", 5),
    "StopFailure": ("blocked", 5),
    "SubagentStop": ("done", 5),
    "SessionEnd": ("done", 5),
}


def build_hook_entry(ai_signal, event, timeout):
    """Return a single matcher object for *event*."""
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": ai_signal,
                "args": ["claude", event, "--quiet"],
                "timeout": timeout,
                "async": True,
            }
        ],
    }


def is_ai_signal_entry(entry):
    """Return True if *entry* looks like it was installed by this script."""
    try:
        for hook in entry.get("hooks", []):
            cmd = hook.get("command", "")
            args = hook.get("args", [])
            if (
                isinstance(args, list)
                and len(args) >= 3
                and args[0] == "claude"
                and args[1] in EVENTS
                and "--quiet" in args
            ):
                return True
            if MARKER_PREFIX in cmd and "claude" in args:
                return True
            if MARKER_PREFIX in cmd and "claude" in cmd:
                return True
    except (AttributeError, TypeError):
        pass
    return False


def strip_ai_signal_entries(hooks_block):
    """Remove ai-signal-managed entries from every event, keep the rest."""
    cleaned = {}
    for event, entries in hooks_block.items():
        remaining = [e for e in entries if not is_ai_signal_entry(e)]
        if remaining:
            cleaned[event] = remaining
    return cleaned


def merge_hooks(existing_hooks, ai_signal_hooks):
    """Merge ai-signal hooks into existing hooks, preserving user entries."""
    merged = dict(existing_hooks)
    for event, entry in ai_signal_hooks.items():
        if event in merged:
            merged[event].append(entry)
        else:
            merged[event] = [entry]
    return merged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ai-signal",
        default=str(Path.home() / ".local" / "bin" / "ai-signal"),
        help="Path to the ai-signal wrapper script",
    )
    parser.add_argument(
        "--settings",
        default=str(DEFAULT_SETTINGS),
        help="Path to Claude Code settings.json",
    )
    args = parser.parse_args()

    settings_path = Path(args.settings)
    ai_signal = str(Path(args.ai_signal).expanduser())

    # Read existing settings
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            print("warning: could not parse {}: {}".format(settings_path, exc))
            settings = {}
    else:
        settings = {}

    # Build the hooks we want to install
    ai_signal_hooks = {}
    for event, (_state, timeout) in EVENTS.items():
        ai_signal_hooks[event] = build_hook_entry(ai_signal, event, timeout)

    # Strip old ai-signal entries, merge fresh ones
    existing_hooks = settings.get("hooks", {})
    if not isinstance(existing_hooks, dict):
        print('warning: existing "hooks" is not an object; replacing it')
        existing_hooks = {}
    cleaned = strip_ai_signal_entries(existing_hooks)
    new_hooks = merge_hooks(cleaned, ai_signal_hooks)

    if existing_hooks == new_hooks:
        print("already up to date: {}".format(settings_path))
        return

    # Backup
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    if settings_path.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = settings_path.with_name(
            settings_path.name + ".bak-ai-signal-{}".format(stamp)
        )
        shutil.copy2(settings_path, backup)
        print("backup: {}".format(backup))

    settings["hooks"] = new_hooks

    tmp = settings_path.with_suffix(settings_path.suffix + ".tmp")
    tmp.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    os.replace(str(tmp), str(settings_path))
    print("updated: {}".format(settings_path))

    # Summary
    print("\nInstalled hooks:")
    for event in sorted(EVENTS):
        print("  {} -> {}".format(event, EVENTS[event][0]))
    print("\nTest with:")
    print("  {}".format(shlex.join([ai_signal, "claude", "PreToolUse", "--session", "demo"])))
    print("  {}".format(shlex.join([ai_signal, "claude", "Stop", "--session", "demo"])))


if __name__ == "__main__":
    main()
