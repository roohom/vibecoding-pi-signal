#!/usr/bin/env python3
"""Install Codex lifecycle hooks into ~/.codex/config.toml."""

import argparse
import os
import shutil
import time
from pathlib import Path

CONFIG = Path.home() / ".codex" / "config.toml"
START = "# >>> ai-signal hooks >>>"
END = "# <<< ai-signal hooks <<<"

EVENTS = {
    "SessionStart": ("SessionStart", 5),
    "UserPromptSubmit": ("UserPromptSubmit", 5),
    "PreToolUse": ("PreToolUse", 5),
    "PostToolUse": ("PostToolUse", 5),
    "PermissionRequest": ("PermissionRequest", 10),
    "SubagentStop": ("SubagentStop", 5),
    "Stop": ("Stop", 5),
}


def toml_string(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_block(ai_signal):
    lines = [START, "[hooks]"]
    for event, (command_event, timeout) in EVENTS.items():
        command = "{} codex {} --quiet".format(ai_signal, command_event)
        lines.append(
            '{} = [{{ hooks = [{{ type = "command", command = {}, timeout = {}, async = true }}] }}]'.format(
                event,
                toml_string(command),
                timeout,
            )
        )
    lines.append(END)
    return "\n".join(lines) + "\n"


def strip_existing_block(text):
    if START not in text:
        return text.rstrip() + "\n"
    before, rest = text.split(START, 1)
    if END not in rest:
        return before.rstrip() + "\n"
    _old, after = rest.split(END, 1)
    return (before.rstrip() + "\n" + after.lstrip()).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ai-signal", default=str(Path.home() / ".local" / "bin" / "ai-signal"))
    args = parser.parse_args()

    old = CONFIG.read_text(encoding="utf-8") if CONFIG.exists() else ""
    new = strip_existing_block(old) + "\n" + build_block(args.ai_signal)
    if old == new:
        print("already up to date: {}".format(CONFIG))
        return

    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG.exists():
        stamp = time.strftime("%Y%m%d-%H%M%S")
        backup = CONFIG.with_name(CONFIG.name + ".bak-ai-signal-toml-{}".format(stamp))
        shutil.copy2(CONFIG, backup)
        print("backup: {}".format(backup))

    tmp = CONFIG.with_suffix(CONFIG.suffix + ".tmp")
    tmp.write_text(new, encoding="utf-8")
    os.replace(str(tmp), str(CONFIG))
    print("updated: {}".format(CONFIG))


if __name__ == "__main__":
    main()
