import tempfile
import unittest
from pathlib import Path

from vibecoding_pi_signal.runtime import SessionStore, SignalRuntime


class FakeClient:
    def __init__(self):
        self.calls = []

    def post_state(self, state, source="", session="", text=""):
        self.calls.append((state, source, session, text))
        return {"ok": True, "state": state}


class RuntimeTest(unittest.TestCase):
    def make_runtime(self):
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        store = SessionStore(Path(tempdir.name) / "sessions.json")
        client = FakeClient()
        runtime = SignalRuntime(client=client, store=store)
        return runtime, client

    def test_permission_wins_over_working(self):
        runtime, client = self.make_runtime()
        runtime.set_session_state("a", "working", "test")
        result = runtime.set_session_state("b", "permission", "test")
        self.assertEqual(result["aggregate_state"], "permission")
        self.assertEqual(client.calls[-1][0], "permission")

    def test_idle_removes_session(self):
        runtime, client = self.make_runtime()
        runtime.set_session_state("a", "blocked", "test")
        result = runtime.set_session_state("a", "idle", "test")
        self.assertEqual(result["aggregate_state"], "idle")
        self.assertEqual(result["sessions"], {})
        self.assertEqual(client.calls[-1][0], "idle")

    def test_clear_sends_off(self):
        runtime, client = self.make_runtime()
        result = runtime.clear_all()
        self.assertEqual(result["aggregate_state"], "off")
        self.assertEqual(client.calls[-1][0], "off")

    def test_stale_session_is_pruned(self):
        runtime, _client = self.make_runtime()
        sessions = {
            "old": {
                "state": "working",
                "source": "test",
                "text": "",
                "updated_at": 1,
            }
        }
        self.assertEqual(runtime.prune_sessions(sessions, now=999999), {})


if __name__ == "__main__":
    unittest.main()
