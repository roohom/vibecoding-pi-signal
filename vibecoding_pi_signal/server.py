"""HTTP-controlled WS2812 signal ring server for Raspberry Pi."""

from __future__ import print_function

import argparse
import json
import math
import signal
import sys
import threading

try:
    from http.server import BaseHTTPRequestHandler, HTTPServer
except ImportError:  # pragma: no cover
    from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

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
        self.state = "off"
        self.meta = {}
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
            level = int(4 + 4 * (1 + math.sin(phase / 7.0)))
            self.ring.fill(color(0, level, 0))
            return 0.18
        if state == "thinking":
            self._spinner(phase, color(10, 0, 24), color(0, 12, 24), color(0, 0, 2))
            return 0.14
        if state == "working":
            self._chase(phase, color(0, 24, 14), color(0, 8, 5))
            return 0.12
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


class RequestHandler(BaseHTTPRequestHandler):
    animator = None

    def do_GET(self):
        if self.path == "/health":
            state, meta = self.animator.get_state()
            return self._json(200, {"ok": True, "state": state, "meta": meta})
        if self.path.startswith("/state/"):
            state = self.path.split("/", 2)[2]
            return self._set_state(state, {"source": "get"})
        return self._json(404, {"ok": False, "error": "not found"})

    def do_POST(self):
        if self.path != "/signal":
            return self._json(404, {"ok": False, "error": "not found"})
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw or "{}")
        except ValueError:
            return self._json(400, {"ok": False, "error": "invalid json"})
        return self._set_state(payload.get("state"), payload)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _set_state(self, state, meta):
        if state not in VALID_STATES:
            return self._json(400, {"ok": False, "error": "unknown state", "state": state})
        self.animator.set_state(state, meta)
        return self._json(200, {"ok": True, "state": state})

    def _json(self, status, body):
        data = json.dumps(body, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
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
