"""Configuration helpers shared by Mac clients and installers."""

import json
import os
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("AI_SIGNAL_CONFIG_DIR", "~/.config/vibecoding-pi-signal")).expanduser()
CONFIG_FILE = Path(os.environ.get("AI_SIGNAL_CONFIG", str(CONFIG_DIR / "config.json"))).expanduser()
STATE_DIR = Path(os.environ.get("SIGNAL_RING_STATE_DIR", "~/.vibecoding-pi-signal")).expanduser()


@dataclass(frozen=True)
class SignalConfig:
    host: str = "raspberrypi.local"
    port: int = 8765
    state_dir: str = str(STATE_DIR)


def load_config(path=None):
    path = Path(path).expanduser() if path else CONFIG_FILE
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        values = {}
    host = os.environ.get("SIGNAL_RING_HOST") or values.get("host") or SignalConfig.host
    port = int(os.environ.get("SIGNAL_RING_PORT") or values.get("port") or SignalConfig.port)
    state_dir = os.environ.get("SIGNAL_RING_STATE_DIR") or values.get("state_dir") or SignalConfig.state_dir
    return SignalConfig(host=host, port=port, state_dir=str(Path(state_dir).expanduser()))


def write_config(host, port=8765, path=None):
    path = Path(path).expanduser() if path else CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"host": host, "port": int(port)}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path
