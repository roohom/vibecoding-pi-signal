import unittest

from vibecoding_pi_signal.hooks.cli import event_to_state, payload_has_session


class HookMappingTest(unittest.TestCase):
    def test_codex_core_events(self):
        self.assertEqual(event_to_state("codex", "UserPromptSubmit", {}), "thinking")
        self.assertEqual(event_to_state("codex", "PreToolUse", {}), "working")
        self.assertEqual(event_to_state("codex", "PermissionRequest", {}), "permission")
        self.assertEqual(event_to_state("codex", "Stop", {}), "idle")

    def test_error_payload_wins(self):
        self.assertEqual(event_to_state("codex", "PostToolUse", {"error": True}), "blocked")

    def test_payload_session_detection(self):
        self.assertTrue(payload_has_session({"session_id": "abc"}))
        self.assertFalse(payload_has_session({}))


if __name__ == "__main__":
    unittest.main()
