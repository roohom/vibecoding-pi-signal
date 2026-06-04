# Mac install

From the project root:

```bash
sh mac/install_mac.sh 192.168.31.131
python3 mac/install_toml_hooks.py
python3 mac/install_refresh_agent.py
```

The Pi host is saved to:

```text
~/.config/vibecoding-pi-signal/config.json
```

Manual tests:

```bash
~/.local/bin/ai-signal codex UserPromptSubmit --session demo
~/.local/bin/ai-signal codex PreToolUse --session demo
~/.local/bin/ai-signal codex PermissionRequest --session demo
~/.local/bin/ai-signal codex Stop --session demo
~/.local/bin/ai-signal manual clear --clear
```

Hook calls are logged to:

```text
~/.vibecoding-pi-signal/hook.log
```
