#!/usr/bin/env python3
"""Remove the older ai-signal notify wrapper from Codex config.toml."""

import ast
import os
import shutil
import time
from pathlib import Path

CONFIG = Path.home() / ".codex" / "config.toml"


def main():
    if not CONFIG.exists():
        print("missing: {}".format(CONFIG))
        return

    lines = CONFIG.read_text(encoding="utf-8").splitlines()
    out = []
    changed = False
    for line in lines:
        if line.startswith("notify = ") and "ai-signal-codex-notify" in line:
            value = line.split("=", 1)[1].strip()
            try:
                items = ast.literal_eval(value)
            except Exception:
                out.append(line)
                continue
            if "--previous-notify" in items:
                items = items[: items.index("--previous-notify")]
                out.append("notify = " + repr(items).replace("'", '"'))
                changed = True
            else:
                out.append(line)
        else:
            out.append(line)

    if not changed:
        print("already clean: {}".format(CONFIG))
        return

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = CONFIG.with_name(CONFIG.name + ".bak-ai-signal-notify-{}".format(stamp))
    shutil.copy2(CONFIG, backup)
    tmp = CONFIG.with_suffix(CONFIG.suffix + ".tmp")
    tmp.write_text("\n".join(out) + "\n", encoding="utf-8")
    os.replace(str(tmp), str(CONFIG))
    print("backup: {}".format(backup))
    print("updated: {}".format(CONFIG))


if __name__ == "__main__":
    main()
