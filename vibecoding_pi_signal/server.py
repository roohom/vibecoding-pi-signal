"""HTTP-controlled WS2812 signal ring server for Raspberry Pi."""

from __future__ import print_function

import argparse
import json
import math
import signal
import sys
import threading
from pathlib import Path

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # pragma: no cover
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

try:
    from urllib.parse import urlparse
except ImportError:  # pragma: no cover
    from urlparse import urlparse

from .config import load_config
from .runtime import SessionStore
from .states import VALID_STATES

try:
    from neopixel import Adafruit_NeoPixel, Color
except ImportError:  # pragma: no cover - only available on Raspberry Pi.
    Adafruit_NeoPixel = None
    Color = None


LED_COUNT = 8
LED_PIN = 18
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_INVERT = False
LED_BRIGHTNESS = 24
LED_CHANNEL = 0
DEFAULT_SETTINGS = {"idle_level": 11, "idle_pixels": 4, "idle_offset": 0}
STATE_ORDER = ("idle", "thinking", "working", "permission", "blocked", "done", "off")


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def color(red, green, blue):
    # The user's ring is wired through the legacy wrapper with red/green swapped.
    return Color(green, red, blue)


class SignalRing:
    def __init__(self, count, pin, brightness):
        if Adafruit_NeoPixel is None:
            raise RuntimeError("neopixel library is required on Raspberry Pi")
        self.strip = Adafruit_NeoPixel(
            count,
            pin,
            LED_FREQ_HZ,
            LED_DMA,
            LED_INVERT,
            brightness,
            LED_CHANNEL,
        )
        self.strip.begin()
        self.lock = threading.Lock()

    def fill(self, pixel_color):
        with self.lock:
            for index in range(self.strip.numPixels()):
                self.strip.setPixelColor(index, pixel_color)
            self.strip.show()

    def set_pixels(self, colors):
        with self.lock:
            for index, pixel_color in enumerate(colors):
                self.strip.setPixelColor(index, pixel_color)
            self.strip.show()

    def off(self):
        self.fill(0)

    def count(self):
        return self.strip.numPixels()


class Animator:
    def __init__(self, ring):
        self.ring = ring
        self.state = "idle"
        self.meta = {"source": "server:start"}
        self.settings = dict(DEFAULT_SETTINGS)
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run)
        self.thread.daemon = True
        self.thread.start()

    def set_state(self, state, meta=None):
        if state not in VALID_STATES:
            raise ValueError("unknown state: {}".format(state))
        with self.lock:
            self.state = state
            self.meta = meta or {}

    def get_state(self):
        with self.lock:
            return self.state, dict(self.meta)

    def get_settings(self):
        with self.lock:
            return dict(self.settings)

    def update_settings(self, payload):
        updates = {}
        if "idle_level" in payload:
            updates["idle_level"] = self._channel_value(payload["idle_level"], "idle_level")
        if "idle_pixels" in payload:
            updates["idle_pixels"] = self._bounded_int(payload["idle_pixels"], "idle_pixels", 0, self.ring.count())
        if "idle_offset" in payload:
            updates["idle_offset"] = self._bounded_int(payload["idle_offset"], "idle_offset", 0, self.ring.count() - 1)
        with self.lock:
            self.settings.update(updates)
            return dict(self.settings)

    def rotate_idle_pixels(self):
        with self.lock:
            self.settings["idle_offset"] = (self.settings["idle_offset"] + 1) % self.ring.count()
            return dict(self.settings)

    def _channel_value(self, value, name):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError("{} must be an integer".format(name))
        if parsed < 0 or parsed > 255:
            raise ValueError("{} must be between 0 and 255".format(name))
        return parsed

    def _bounded_int(self, value, name, minimum, maximum):
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            raise ValueError("{} must be an integer".format(name))
        if parsed < minimum or parsed > maximum:
            raise ValueError("{} must be between {} and {}".format(name, minimum, maximum))
        return parsed

    def close(self):
        self.stop_event.set()
        self.thread.join(2)
        self.ring.off()

    def _run(self):
        phase = 0
        while not self.stop_event.is_set():
            state, _meta = self.get_state()
            delay = self._draw(state, phase)
            phase = (phase + 1) % 1024
            self.stop_event.wait(delay)

    def _draw(self, state, phase):
        if state == "off":
            self.ring.off()
            return 0.5
        if state == "idle":
            settings = self.get_settings()
            pixels = [0] * self.ring.count()
            for index in self._evenly_spaced_indexes(settings["idle_pixels"]):
                pixel_index = (index + settings["idle_offset"]) % self.ring.count()
                pixels[pixel_index] = color(0, settings["idle_level"], 0)
            self.ring.set_pixels(pixels)
            return 1.0
        if state == "thinking":
            self._spinner(phase, color(10, 0, 24), color(0, 12, 24), color(0, 0, 2))
            return 0.14
        if state == "working":
            level = self.get_settings()["idle_level"]
            trail = max(1, level // 3)
            self._chase(phase, color(0, level, level), color(0, trail, trail))
            return 0.28
        if state == "permission":
            self.ring.fill(color(28, 16, 0) if phase % 8 < 3 else 0)
            return 0.24
        if state == "blocked":
            self.ring.fill(color(34, 0, 0) if phase % 6 < 3 else 0)
            return 0.18
        if state == "done":
            level = int(7 + 7 * (1 + math.sin(phase / 4.0)))
            self.ring.fill(color(0, level, 0))
            return 0.18
        self.ring.off()
        return 0.5

    def _spinner(self, phase, primary, secondary, background):
        pixels = []
        head = phase % self.ring.count()
        for index in range(self.ring.count()):
            if index == head:
                pixels.append(primary)
            elif index == (head - 1) % self.ring.count():
                pixels.append(secondary)
            else:
                pixels.append(background)
        self.ring.set_pixels(pixels)

    def _chase(self, phase, primary, trail):
        pixels = []
        head = phase % self.ring.count()
        for index in range(self.ring.count()):
            if index == head:
                pixels.append(primary)
            elif index == (head - 1) % self.ring.count():
                pixels.append(trail)
            else:
                pixels.append(0)
        self.ring.set_pixels(pixels)

    def _evenly_spaced_indexes(self, lit_count):
        count = self.ring.count()
        if lit_count <= 0:
            return []
        if lit_count >= count:
            return list(range(count))
        return sorted(set(int(index * count / float(lit_count)) for index in range(lit_count)))


def render_console_html():
    states = json.dumps(STATE_ORDER)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Pi Signal Console</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f7f8f5;
      --panel: #ffffff;
      --ink: #1d2524;
      --muted: #65706e;
      --line: #d9dfdc;
      --accent: #167c75;
      --danger: #b3261e;
      --warn: #9b6400;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font: 15px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid var(--line);
      background: #ffffff;
    }
    h1, h2 { margin: 0; font-size: 18px; letter-spacing: 0; }
    h2 { font-size: 15px; }
    main {
      width: min(1040px, calc(100vw - 32px));
      margin: 18px auto 28px;
      display: grid;
      grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
      gap: 16px;
    }
    section {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }
    .status {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }
    .dot {
      width: 16px;
      height: 16px;
      border-radius: 50%;
      background: #a0a8a5;
      box-shadow: 0 0 0 4px rgba(22, 124, 117, 0.1);
      flex: 0 0 auto;
    }
    .state-name { font-size: 26px; font-weight: 700; }
    .muted { color: var(--muted); }
    .grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 14px;
    }
    button {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      font: inherit;
      cursor: pointer;
    }
    button:hover { border-color: var(--accent); }
    button.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #fff;
    }
    button.danger { color: var(--danger); }
    label {
      display: grid;
      gap: 6px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 13px;
    }
    input[type="range"] { width: 100%; }
    input[type="number"], input[type="text"] {
      width: 100%;
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 7px 9px;
      font: inherit;
      color: var(--ink);
      background: #fff;
    }
    .row {
      display: grid;
      grid-template-columns: 1fr 72px;
      gap: 10px;
      align-items: end;
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      margin: 12px 0 0;
      padding: 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f2f5f3;
      color: #26302e;
      min-height: 92px;
      max-height: 220px;
      overflow: auto;
    }
    .meta {
      display: grid;
      grid-template-columns: 100px minmax(0, 1fr);
      gap: 7px 10px;
      margin-top: 14px;
      color: var(--muted);
    }
    .meta b { color: var(--ink); font-weight: 600; }
    .actions {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 14px;
    }
    @media (max-width: 760px) {
      header { align-items: flex-start; flex-direction: column; padding: 16px; }
      main { grid-template-columns: 1fr; width: calc(100vw - 24px); margin-top: 12px; }
      .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .state-name { font-size: 22px; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Pi Signal Console</h1>
      <div class="muted" id="endpoint"></div>
    </div>
    <button class="primary" id="refresh">Refresh</button>
  </header>
  <main>
    <section>
      <div class="status">
        <div class="dot" id="dot"></div>
        <div>
          <div class="state-name" id="state">unknown</div>
          <div class="muted" id="summary">Waiting for signal service</div>
        </div>
      </div>
      <div class="grid" id="stateButtons"></div>
      <div class="actions">
        <button id="clearIdle">Clear to idle</button>
        <button class="danger" id="turnOff">Turn off</button>
      </div>
      <div class="meta" id="meta"></div>
    </section>
    <section>
      <h2>Idle settings</h2>
      <label>
        Idle brightness
        <div class="row">
          <input id="idleLevel" type="range" min="0" max="255" value="11">
          <input id="idleLevelNumber" type="number" min="0" max="255" value="11">
        </div>
      </label>
      <label>
        Lit pixels
        <input id="idlePixels" type="number" min="0" max="64" value="4">
      </label>
      <label>
        Pixel offset
        <input id="idleOffset" type="number" min="0" max="63" value="0">
      </label>
      <div class="actions">
        <button class="primary" id="saveConfig">Apply</button>
        <button id="testIdle">Apply and show idle</button>
      </div>
      <h2 style="margin-top:18px">Mac command</h2>
      <input id="macCommand" type="text" readonly>
      <pre id="log"></pre>
    </section>
  </main>
  <script>
    const states = """ + states + """;
    const colors = {
      idle: "#2f8f46",
      thinking: "#5798db",
      working: "#20a59b",
      permission: "#d99a23",
      blocked: "#c9342f",
      done: "#34a853",
      off: "#8a928f"
    };
    const $ = (id) => document.getElementById(id);
    const log = (text) => { $("log").textContent = new Date().toLocaleTimeString() + "  " + text + "\\n" + $("log").textContent; };
    const api = async (path, options = {}) => {
      const res = await fetch(path, options);
      const data = await res.json();
      if (!res.ok || data.ok === false) throw new Error(data.error || res.statusText);
      return data;
    };
    const setNumberPair = (value) => {
      $("idleLevel").value = value;
      $("idleLevelNumber").value = value;
    };
    const setState = async (state, source = "web-console") => {
      await api("/signal", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({state, source, session: "web-console", text: state})
      });
      log("state -> " + state);
      await refresh();
    };
    const saveConfig = async () => {
      const payload = {
        idle_level: Number($("idleLevelNumber").value),
        idle_pixels: Number($("idlePixels").value),
        idle_offset: Number($("idleOffset").value)
      };
      const data = await api("/config", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload)
      });
      applySettings(data.settings);
      log("config saved");
    };
    const applySettings = (settings) => {
      if (!settings) return;
      setNumberPair(settings.idle_level);
      $("idlePixels").value = settings.idle_pixels;
      $("idleOffset").value = settings.idle_offset;
    };
    const refresh = async () => {
      try {
        const data = await api("/health");
        $("state").textContent = data.state;
        $("summary").textContent = data.meta && data.meta.source ? data.meta.source : "No source metadata";
        $("dot").style.background = colors[data.state] || colors.off;
        applySettings(data.settings);
        const meta = data.meta || {};
        $("meta").innerHTML = [
          ["source", meta.source || ""],
          ["session", meta.session || ""],
          ["text", meta.text || ""],
          ["idle", JSON.stringify(data.settings || {})]
        ].map(([k, v]) => "<span>" + k + "</span><b>" + String(v).replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) + "</b>").join("");
      } catch (err) {
        $("summary").textContent = err.message;
        log("error: " + err.message);
      }
    };
    const init = () => {
      $("endpoint").textContent = location.origin;
      $("macCommand").value = "~/.local/bin/ai-signal manual configure --configure --host " + location.hostname + " --port " + location.port;
      $("stateButtons").innerHTML = states.map((state) => "<button data-state='" + state + "'>" + state + "</button>").join("");
      $("stateButtons").addEventListener("click", (event) => {
        const state = event.target.getAttribute("data-state");
        if (state) setState(state).catch((err) => log("error: " + err.message));
      });
      $("refresh").onclick = refresh;
      $("clearIdle").onclick = () => setState("idle", "web-console:clear").catch((err) => log("error: " + err.message));
      $("turnOff").onclick = () => setState("off").catch((err) => log("error: " + err.message));
      $("saveConfig").onclick = () => saveConfig().catch((err) => log("error: " + err.message));
      $("testIdle").onclick = () => saveConfig().then(() => setState("idle")).catch((err) => log("error: " + err.message));
      $("idleLevel").oninput = () => { $("idleLevelNumber").value = $("idleLevel").value; };
      $("idleLevelNumber").oninput = () => { $("idleLevel").value = $("idleLevelNumber").value; };
      refresh();
      setInterval(refresh, 3000);
    };
    init();
  </script>
</body>
</html>
"""


def clear_local_sessions():
    config = load_config()
    SessionStore(Path(config.state_dir) / "sessions.json").save({})


class RequestHandler(BaseHTTPRequestHandler):
    animator = None

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/console"):
            return self._html(200, render_console_html())
        if path == "/health":
            state, meta = self.animator.get_state()
            return self._json(200, {"ok": True, "state": state, "meta": meta, "settings": self.animator.get_settings()})
        if path == "/config":
            return self._json(200, {"ok": True, "settings": self.animator.get_settings()})
        if path.startswith("/state/"):
            state = path.split("/", 2)[2]
            return self._set_state(state, {"source": "get"})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/signal", "/config"):
            return self._json(404, {"ok": False, "error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw or "{}")
        except ValueError:
            return self._json(400, {"ok": False, "error": "invalid json"})
        if path == "/config":
            return self._update_config(payload)
        return self._set_state(payload.get("state"), payload)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _set_state(self, state, meta):
        if state not in VALID_STATES:
            return self._json(400, {"ok": False, "error": "unknown state", "state": state})
        if state == "idle" and meta.get("source", "").endswith(":SessionStart"):
            self.animator.rotate_idle_pixels()
        if state == "idle" and meta.get("source") == "web-console:clear":
            clear_local_sessions()
        self.animator.set_state(state, meta)
        return self._json(200, {"ok": True, "state": state})

    def _update_config(self, payload):
        try:
            settings = self.animator.update_settings(payload)
        except ValueError as exc:
            return self._json(400, {"ok": False, "error": str(exc)})
        return self._json(200, {"ok": True, "settings": settings})

    def _json(self, status, body):
        data = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, status, body):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--count", type=int, default=LED_COUNT)
    parser.add_argument("--pin", type=int, default=LED_PIN)
    parser.add_argument("--brightness", type=int, default=LED_BRIGHTNESS)
    args = parser.parse_args(argv)

    ring = SignalRing(args.count, args.pin, args.brightness)
    animator = Animator(ring)
    RequestHandler.animator = animator
    server = ReusableHTTPServer((args.host, args.port), RequestHandler)

    def shutdown(_signum, _frame):
        raise SystemExit

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    print("signal ring listening on {}:{}".format(args.host, args.port))
    try:
        server.serve_forever()
    finally:
        animator.close()
        server.server_close()


if __name__ == "__main__":
    main()
