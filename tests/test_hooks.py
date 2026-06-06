import tempfile
import unittest
import unittest.mock
from pathlib import Path

from vibecoding_pi_signal.config import SignalConfig
from vibecoding_pi_signal.hooks.cli import event_to_state, main, payload_has_session, should_ignore_event


class HookMappingTest(unittest.TestCase):
    def test_codex_core_events(self):
        self.assertEqual(event_to_state("codex", "UserPromptSubmit", {}), "thinking")
        self.assertEqual(event_to_state("codex", "PreToolUse", {}), "working")
        self.assertEqual(event_to_state("codex", "PermissionRequest", {}), "permission")
        self.assertEqual(event_to_state("codex", "Stop", {}), "idle")

    def test_error_payload_wins(self):
        self.assertEqual(event_to_state("codex", "PostToolUse", {"error": True}), "blocked")

    def test_claude_core_events(self):
        self.assertEqual(event_to_state("claude", "UserPromptSubmit", {}), "thinking")
        self.assertEqual(event_to_state("claude", "PreToolUse", {}), "working")
        self.assertEqual(event_to_state("claude", "PermissionRequest", {}), "permission")
        self.assertEqual(event_to_state("claude", "StopFailure", {}), "blocked")
        self.assertEqual(event_to_state("claude", "Stop", {}), "idle")

    def test_payload_session_detection(self):
        self.assertTrue(payload_has_session({"session_id": "abc"}))
        self.assertFalse(payload_has_session({}))

    def test_codex_background_ambient_prompt_is_ignored(self):
        text = "You are an expert at upholding safety and compliance standards for Codex ambient suggestions."
        self.assertTrue(should_ignore_event("codex", "UserPromptSubmit", {}, text))

    def test_unknown_codex_event_is_conservative(self):
        self.assertEqual(event_to_state("codex", "RuntimeRefresh", {}), "idle")
        self.assertTrue(should_ignore_event("codex", "RuntimeRefresh", {}, "RuntimeRefresh"))

    def test_ignored_codex_event_does_not_write_session(self):
        with tempfile.TemporaryDirectory() as tempdir:
            config = SignalConfig(host="localhost", port=8765, state_dir=tempdir)
            argv = [
                "codex",
                "UserPromptSubmit",
                "--session",
                "ambient",
                "--text",
                "Generate 0 to 3 hyperpersonalized suggestions for what this user can do with Codex.",
                "--json",
            ]
            with unittest.mock.patch("vibecoding_pi_signal.hooks.cli.load_config", return_value=config):
                self.assertEqual(main(argv), 0)

            self.assertFalse((Path(tempdir) / "sessions.json").exists())


if __name__ == "__main__":
    unittest.main()
