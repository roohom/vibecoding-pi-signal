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

    def test_clear_sends_idle(self):
        runtime, client = self.make_runtime()
        result = runtime.clear_all()
        self.assertEqual(result["aggregate_state"], "idle")
        self.assertEqual(client.calls[-1][0], "idle")

    def test_clear_sessions_by_prefix_keeps_other_agents(self):
        runtime, client = self.make_runtime()
        runtime.set_session_state("codex:a", "working", "test")
        runtime.set_session_state("claude:b", "permission", "test")
        result = runtime.clear_sessions_by_prefix("codex:", source="test")
        self.assertEqual(result["aggregate_state"], "permission")
        self.assertIn("claude:b", result["sessions"])
        self.assertNotIn("codex:a", result["sessions"])
        self.assertEqual(client.calls[-1][0], "permission")

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

    def test_stale_active_session_is_pruned(self):
        runtime, _client = self.make_runtime()
        sessions = {
            "old": {
                "state": "working",
                "source": "test",
                "text": "",
                "updated_at": 1,
            }
        }
        self.assertEqual(runtime.prune_sessions(sessions, now=1302), {})

    def test_permission_does_not_use_active_session_ttl(self):
        runtime, _client = self.make_runtime()
        sessions = {
            "old": {
                "state": "permission",
                "source": "test",
                "text": "",
                "updated_at": 1,
            }
        }
        self.assertEqual(runtime.prune_sessions(sessions, now=1302), sessions)

    def test_refresh_prunes_stored_codex_ambient_session(self):
        runtime, client = self.make_runtime()
        runtime.store.save(
            {
                "codex:ambient": {
                    "state": "thinking",
                    "source": "codex:UserPromptSubmit",
                    "text": "You are an expert at upholding safety and compliance standards for Codex ambient suggestions.",
                    "updated_at": 1000,
                }
            }
        )

        result = runtime.refresh()

        self.assertEqual(result["aggregate_state"], "idle")
        self.assertEqual(result["sessions"], {})
        self.assertEqual(runtime.store.load(), {})
        self.assertEqual(client.calls[-1], ("idle", "runtime:refresh", "aggregate", ""))

    def test_clear_all_prevents_old_working_session_from_refreshing(self):
        runtime, client = self.make_runtime()
        runtime.set_session_state("codex:a", "working", "test")

        runtime.clear_all()
        result = runtime.refresh()

        self.assertEqual(result["aggregate_state"], "idle")
        self.assertEqual(result["sessions"], {})
        self.assertEqual(client.calls[-1][0], "idle")


if __name__ == "__main__":
    unittest.main()
