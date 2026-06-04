#!/usr/bin/env python3
"""Install a launchd agent that refreshes expired signal sessions."""

import subprocess
from pathlib import Path

PLIST = Path.home() / "Library" / "LaunchAgents" / "com.roohom.ai-signal-refresh.plist"
LABEL = "com.roohom.ai-signal-refresh"
AI_SIGNAL = str(Path.home() / ".local" / "bin" / "ai-signal")

PLIST_CONTENT = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{label}</string>
  <key>ProgramArguments</key>
  <array>
    <string>{ai_signal}</string>
    <string>manual</string>
    <string>refresh</string>
    <string>--refresh</string>
  </array>
  <key>StartInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>/tmp/ai-signal-refresh.log</string>
  <key>StandardErrorPath</key>
  <string>/tmp/ai-signal-refresh.err</string>
</dict>
</plist>
"""


def main():
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(PLIST_CONTENT.format(label=LABEL, ai_signal=AI_SIGNAL), encoding="utf-8")
    subprocess.run(["launchctl", "unload", str(PLIST)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    subprocess.run(["launchctl", "load", str(PLIST)], check=True)
    print("Installed {}".format(PLIST))


if __name__ == "__main__":
    main()
