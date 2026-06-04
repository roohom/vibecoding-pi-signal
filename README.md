# Vibecoding Pi Signal Ring

A portable Raspberry Pi signal light for AI coding agents. The Pi owns the LED
animation loop, and each Mac sends Codex or Claude Code lifecycle events over
the local network.

This version is built around an 8-pixel WS2812/NeoPixel ring, but the Mac side
only speaks a small state protocol, so the Pi renderer can later be replaced
with a dot-matrix display, LCD, or another signal device.

## States

```text
idle       soft green breathing
thinking   purple/blue spinner
working    dim green chase
permission amber flashes, slower interval
blocked    red flashes, shorter interval
done       short green breathing
off        LEDs off
```

Concurrent sessions are aggregated on the Mac by priority:

```text
blocked > permission > working > thinking > done > idle
```

## Raspberry Pi

On the Pi:

```bash
cd /home/pi/vibecoding-pi-signal
sh pi/install_service.sh
```

Optional hardware overrides:

```bash
BRIGHTNESS=24 LED_COUNT=8 LED_PIN=18 PORT=8765 sh pi/install_service.sh
```

Endpoints:

```text
GET  /health
GET  /state/<state>
POST /signal {"state":"working","source":"codex","session":"abc"}
```

## Mac

From this project directory on each Mac:

```bash
sh mac/install_mac.sh 192.168.31.131
python3 mac/install_toml_hooks.py
python3 mac/install_refresh_agent.py
```

Manual tests:

```bash
~/.local/bin/ai-signal codex UserPromptSubmit --session demo
~/.local/bin/ai-signal codex PreToolUse --session demo
~/.local/bin/ai-signal codex PermissionRequest --session demo
~/.local/bin/ai-signal codex Stop --session demo
~/.local/bin/ai-signal manual clear --clear
```

The Pi address is stored in:

```text
~/.config/vibecoding-pi-signal/config.json
```

You can override it per command:

```bash
SIGNAL_RING_HOST=192.168.31.131 ~/.local/bin/ai-signal codex PreToolUse --session demo
```

## Codex Integration

Current Codex desktop builds use lifecycle hooks in `~/.codex/config.toml`.
The installer writes a managed `[hooks]` block and creates a timestamped backup.

```bash
python3 mac/install_toml_hooks.py
```

Hook mapping:

```text
SessionStart      -> idle
UserPromptSubmit  -> thinking
PreToolUse        -> working
PostToolUse       -> working
PermissionRequest -> permission
SubagentStop      -> done
Stop              -> idle
Error             -> blocked
```

Hook invocations are logged to:

```text
~/.vibecoding-pi-signal/hook.log
```

If you previously installed the older Codex notify wrapper, remove it after TOML
hooks are working:

```bash
python3 mac/remove_legacy_notify.py
```

## Project Layout

```text
vibecoding_pi_signal/   shared Python package
mac/                    macOS install and compatibility scripts
pi/                     Raspberry Pi service installer and wrapper
docs/                   install and troubleshooting notes
tests/                  unit tests for runtime and hook behavior
```

## Development

```bash
python3 -m unittest discover -s tests
python3 mac/signal_client.py working --host 192.168.31.131
python3 mac/signal_client.py off --host 192.168.31.131
```

See also:

```text
docs/ARCHITECTURE.md
docs/INSTALL_MAC.md
docs/INSTALL_PI.md
docs/CODEX_HOOKS.md
docs/TROUBLESHOOTING.md
```

## License

MIT
