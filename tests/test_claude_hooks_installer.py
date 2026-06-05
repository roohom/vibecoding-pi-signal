import importlib.util
import tempfile
import unittest
import unittest.mock
from pathlib import Path


INSTALLER_PATH = Path(__file__).resolve().parents[1] / "mac" / "install_claude_hooks.py"
SPEC = importlib.util.spec_from_file_location("install_claude_hooks", INSTALLER_PATH)
install_claude_hooks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(install_claude_hooks)


class ClaudeHookInstallerTest(unittest.TestCase):
    def test_build_hook_entry_uses_structured_async_command(self):
        entry = install_claude_hooks.build_hook_entry("/tmp/ai signal", "PreToolUse", 5)
        hook = entry["hooks"][0]

        self.assertEqual(entry["matcher"], "")
        self.assertEqual(hook["type"], "command")
        self.assertEqual(hook["command"], "/tmp/ai signal")
        self.assertEqual(hook["args"], ["claude", "PreToolUse", "--quiet"])
        self.assertEqual(hook["timeout"], 5)
        self.assertIs(hook["async"], True)

    def test_merge_preserves_user_hooks_and_replaces_ai_signal_hooks(self):
        existing = {
            "PreToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [{"type": "command", "command": "echo user hook"}],
                },
                install_claude_hooks.build_hook_entry("/old/ai-signal", "PreToolUse", 5),
            ],
            "PostToolUse": [
                {
                    "matcher": "",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "nohup /old/ai-signal claude PostToolUse --quiet >/dev/null 2>&1 &",
                        }
                    ],
                }
            ],
        }
        fresh = {
            "PreToolUse": install_claude_hooks.build_hook_entry(
                "/new/ai-signal", "PreToolUse", 5
            ),
            "PostToolUse": install_claude_hooks.build_hook_entry(
                "/new/ai-signal", "PostToolUse", 5
            ),
        }

        cleaned = install_claude_hooks.strip_ai_signal_entries(existing)
        merged = install_claude_hooks.merge_hooks(cleaned, fresh)

        self.assertEqual(len(merged["PreToolUse"]), 2)
        self.assertEqual(merged["PreToolUse"][0]["matcher"], "Bash")
        self.assertEqual(merged["PreToolUse"][1]["hooks"][0]["command"], "/new/ai-signal")
        self.assertEqual(len(merged["PostToolUse"]), 1)
        self.assertEqual(merged["PostToolUse"][0]["hooks"][0]["command"], "/new/ai-signal")

    def test_event_coverage_matches_runtime_expectations(self):
        self.assertIn("UserPromptSubmit", install_claude_hooks.EVENTS)
        self.assertIn("PermissionRequest", install_claude_hooks.EVENTS)
        self.assertIn("StopFailure", install_claude_hooks.EVENTS)
        self.assertEqual(install_claude_hooks.EVENTS["StopFailure"][0], "blocked")

    def test_installer_main_is_idempotent_for_path_with_spaces(self):
        with tempfile.TemporaryDirectory() as tempdir:
            settings = Path(tempdir) / "settings.json"
            argv = [
                "install_claude_hooks.py",
                "--settings",
                str(settings),
                "--ai-signal",
                "/tmp/ai signal",
            ]

            with unittest.mock.patch("sys.argv", argv):
                install_claude_hooks.main()
            first = settings.read_text(encoding="utf-8")

            with unittest.mock.patch("sys.argv", argv):
                install_claude_hooks.main()
            second = settings.read_text(encoding="utf-8")

            self.assertEqual(first, second)
            self.assertIn('"command": "/tmp/ai signal"', second)
            self.assertNotIn("nohup", second)

    def test_installer_expands_user_path(self):
        with tempfile.TemporaryDirectory() as tempdir:
            settings = Path(tempdir) / "settings.json"
            argv = [
                "install_claude_hooks.py",
                "--settings",
                str(settings),
                "--ai-signal",
                "~/.local/bin/ai-signal",
            ]

            with unittest.mock.patch("sys.argv", argv):
                install_claude_hooks.main()

            text = settings.read_text(encoding="utf-8")
            self.assertIn(str(Path.home() / ".local" / "bin" / "ai-signal"), text)
            self.assertNotIn('"command": "~/', text)


if __name__ == "__main__":
    unittest.main()
