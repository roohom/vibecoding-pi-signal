# Vibecoding Pi Signal Ring

A portable Raspberry Pi signal light for AI coding agents. The Pi owns the LED
animation loop, and each Mac sends Codex or Claude Code lifecycle events over
the local network.

This version is built around an 8-pixel WS2812/NeoPixel ring, but the Mac side
only speaks a small state protocol, so the Pi renderer can later be replaced
with a dot-matrix display, LCD, or another signal device.

## Inspiration

This project is inspired by and references the excellent idea and interaction
model from [starlight36/vibecoding-signal-light](https://github.com/starlight36/vibecoding-signal-light).
Thanks to that project for proving that an external ambient signal can make AI
coding agent state visible without pulling attention back into the terminal.

This Raspberry Pi version keeps the same core spirit while using a small HTTP
state protocol and a replaceable Pi-side renderer, so the hardware can evolve
from a signal ring to a dot-matrix screen or LCD later.

## States

```text
idle       very low green steady
thinking   purple/blue spinner
working    subtle dim teal chase
permission amber flashes, needs user action
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
GET  /config
POST /config {"idle_level":11,"idle_pixels":4,"idle_offset":0}
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

## Moving to Another Network or Mac

When you take the Raspberry Pi to another network, its LAN IP will probably
change. The Mac side only needs to know the Pi host and port, so reconnecting is
usually just a one-command reconfiguration.

### Same LAN, Bonjour Works

If the new Mac and the Pi are on the same Wi-Fi/LAN, try the Pi's `.local` name
first:

```bash
curl http://raspberrypi.local:8765/health
sh mac/install_mac.sh raspberrypi.local
python3 mac/install_toml_hooks.py
python3 mac/install_refresh_agent.py
```

Then test a state change:

```bash
~/.local/bin/ai-signal codex PreToolUse --session test
~/.local/bin/ai-signal codex Stop
```

### Same LAN, Bonjour Does Not Work

Find the Pi's new IP address from your router, network scanner, or the Pi's
terminal, then configure the Mac with that IP:

```bash
sh mac/install_mac.sh 10.20.30.45
```

If the wrapper is already installed, update only the saved host:

```bash
~/.local/bin/ai-signal manual configure --configure --host 10.20.30.45 --port 8765
```

### Best Long-Term Option: Tailscale

Company Wi-Fi often blocks device-to-device LAN traffic, even when the Mac and
Pi appear to be on the same network. For the most reliable portable setup,
install Tailscale on both the Raspberry Pi and each Mac, then configure this
project with the Pi's Tailscale IP or MagicDNS name:

```bash
sh mac/install_mac.sh raspberrypi
```

or:

```bash
sh mac/install_mac.sh 100.x.y.z
```

This keeps the signal light working across home, office, and travel networks
without chasing changing LAN IPs.

### Before You Leave

Make sure the Pi can join the destination network. Either preconfigure the new
Wi-Fi on the Pi, use Ethernet, or bring a known hotspot. If the Pi is offline,
the Mac cannot discover or control the signal service.

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
