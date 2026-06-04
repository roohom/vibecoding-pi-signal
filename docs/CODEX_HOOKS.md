# Codex hooks

Current Codex desktop builds read lifecycle hooks from `~/.codex/config.toml`.
This project manages only the block between:

```text
# >>> ai-signal hooks >>>
# <<< ai-signal hooks <<<
```

Install or refresh the hook block:

```bash
python3 mac/install_toml_hooks.py
```

Installed mapping:

```text
SessionStart      -> idle
UserPromptSubmit  -> thinking
PreToolUse        -> working
PostToolUse       -> working
PermissionRequest -> permission
SubagentStop      -> done
Stop              -> idle
Error             -> blocked
```

Older `~/.codex/hooks.json` configs were used by some examples, but they are not
the integration path for this Codex desktop version.
