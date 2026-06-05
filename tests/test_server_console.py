import io
import json
import unittest

from vibecoding_pi_signal.server import RequestHandler, render_console_html


class FakeAnimator:
    def __init__(self):
        self.state = "off"
        self.meta = {}
        self.settings = {"idle_level": 11, "idle_pixels": 4, "idle_offset": 0}

    def get_state(self):
        return self.state, dict(self.meta)

    def get_settings(self):
        return dict(self.settings)

    def set_state(self, state, meta=None):
        self.state = state
        self.meta = meta or {}

    def update_settings(self, payload):
        self.settings.update(payload)
        return dict(self.settings)

    def rotate_idle_pixels(self):
        self.settings["idle_offset"] = self.settings["idle_offset"] + 1
        return dict(self.settings)


class TestableHandler(RequestHandler):
    def __init__(self, method, path, body=None):
        self.path = path
        raw = json.dumps(body).encode("utf-8") if body is not None else b""
        self.headers = {"Content-Length": str(len(raw))}
        self.rfile = io.BytesIO(raw)
        self.status = None
        self.content_type = None
        self.body = None

    def _json(self, status, body):
        self.status = status
        self.content_type = "application/json"
        self.body = body
        return body

    def _html(self, status, body):
        self.status = status
        self.content_type = "text/html"
        self.body = body
        return body


class ServerConsoleTest(unittest.TestCase):
    def setUp(self):
        self.animator = FakeAnimator()
        RequestHandler.animator = self.animator
        TestableHandler.animator = self.animator

    def test_console_html_contains_expected_api_hooks(self):
        html = render_console_html()
        self.assertIn("Pi Signal Console", html)
        self.assertIn("/health", html)
        self.assertIn("/signal", html)
        self.assertIn("/config", html)

    def test_console_page_is_served_at_root(self):
        handler = TestableHandler("GET", "/")
        handler.do_GET()

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.content_type, "text/html")
        self.assertIn("Pi Signal Console", handler.body)

    def test_health_still_returns_json(self):
        self.animator.set_state("working", {"source": "test"})
        handler = TestableHandler("GET", "/health")
        handler.do_GET()

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.content_type, "application/json")
        self.assertEqual(handler.body["state"], "working")
        self.assertEqual(handler.body["meta"]["source"], "test")

    def test_console_can_update_config_and_state(self):
        handler = TestableHandler(
            "POST",
            "/config",
            {"idle_level": 18, "idle_pixels": 5, "idle_offset": 2},
        )
        handler.do_POST()

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.body["settings"]["idle_level"], 18)

        handler = TestableHandler(
            "POST",
            "/signal",
            {"state": "idle", "source": "web-console", "session": "web-console"},
        )
        handler.do_POST()

        self.assertEqual(handler.status, 200)
        self.assertEqual(handler.body["state"], "idle")
        self.assertEqual(self.animator.state, "idle")


if __name__ == "__main__":
    unittest.main()
