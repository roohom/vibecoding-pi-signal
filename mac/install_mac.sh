#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=${APP_DIR:-$(dirname "$SCRIPT_DIR")}
BIN_DIR=${BIN_DIR:-$HOME/.local/bin}
HOST=${SIGNAL_RING_HOST:-${1:-192.168.31.131}}
PORT=${SIGNAL_RING_PORT:-8765}

mkdir -p "$BIN_DIR" "$HOME/.vibecoding-pi-signal" "$HOME/.config/vibecoding-pi-signal"

"$APP_DIR/mac/agent_hook.py" manual configure --configure --host "$HOST" --port "$PORT" >/dev/null

cat > "$BIN_DIR/ai-signal" <<SCRIPT
#!/bin/sh
cd "$APP_DIR"
exec /usr/bin/python3 -m vibecoding_pi_signal.hooks.cli "\$@"
SCRIPT

chmod +x "$BIN_DIR/ai-signal"

echo "Installed $BIN_DIR/ai-signal"
echo "Configured Pi: $HOST:$PORT"
echo "Try: $BIN_DIR/ai-signal codex PreToolUse --session demo"
