"""Command-line hook adapter for Codex, Claude Code, and manual tests."""

import argparse
import json
import os
import select
import sys
import time
from pathlib import Path

from ..client import SignalClient
from ..config import load_config, write_config
from ..runtime import SignalRuntime
from ..states import AGENT_EVENT_MAPS, is_codex_background_text


SESSION_KEYS = ("session_id", "sessionId", "conversation_id", "conversationId", "cwd")
TERMINAL_EVENTS = {"Stop", "stop", "SessionEnd", "sessionEnd"}
RUNTIME_REFRESH_EVENTS = {"runtime:refresh", "runtimeRefresh"}


def read_stdin_json():
    if sys.stdin.isatty():
        return {}
    ready, _, _ = select.select([sys.stdin], [], [], 0)
    if not ready:
        return {}
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {"raw": raw}


def infer_session(agent, payload, fallback):
    for key in SESSION_KEYS:
        value = payload.get(key)
        if value:
            return "{}:{}".format(agent, value)
    return "{}:{}".format(agent, fallback)


def infer_text(event, payload):
    for key in ("command", "tool_name", "tool", "message", "prompt"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value[:160]
    return event


def event_to_state(agent, event, payload):
    if payload.get("state"):
        return payload["state"]
    if payload.get("error") or payload.get("blocked"):
        return "blocked"
    mapping = AGENT_EVENT_MAPS.get(agent, {})
    if agent == "codex":
        return mapping.get(event, "idle")
    return mapping.get(event, "working")


def should_ignore_event(agent, event, payload, text=""):
    if (
        agent != "codex"
        or payload.get("state")
        or payload.get("error")
        or payload.get("blocked")
    ):
        return False
    if event in RUNTIME_REFRESH_EVENTS or payload.get("source") in RUNTIME_REFRESH_EVENTS:
        return True
    if is_codex_background_text(text) or is_codex_background_text(payload.get("prompt")):
        return True
    return event not in AGENT_EVENT_MAPS.get(agent, {})


def payload_has_session(payload):
    return any(payload.get(key) for key in SESSION_KEYS)


def append_hook_log(agent, event, session, state):
    directory = Path("~/.vibecoding-pi-signal").expanduser()
    try:
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "hook.log").open("a", encoding="utf-8") as handle:
            handle.write(
                "{}\tagent={}\tevent={}\tsession={}\tstate={}\n".format(
                    time.strftime("%Y-%m-%dT%H:%M:%S"),
                    agent,
                    event,
                    session,
                    state,
                )
            )
    except Exception:
        pass


def build_runtime(args):
    config = load_config()
    host = args.host or config.host
    port = args.port or config.port
    client = SignalClient(host, port)
    return SignalRuntime(client=client, config=config)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("agent", choices=["codex", "claude", "manual"])
    parser.add_argument("event", nargs="?", default="")
    parser.add_argument("--session", default="")
    parser.add_argument("--state", default="")
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--text", default="")
    parser.add_argument("--clear", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--configure", action="store_true", help="persist --host/--port in the user config")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    try:
        if args.configure:
            if not args.host:
                raise SystemExit("--configure requires --host")
            path = write_config(args.host, args.port or 8765)
            result = {"ok": True, "config": str(path), "host": args.host, "port": args.port or 8765}
        else:
            runtime = build_runtime(args)
            if args.clear:
                result = runtime.clear_all()
            elif args.refresh:
                result = runtime.refresh()
            else:
                payload = read_stdin_json()
                event = args.event or payload.get("hook_event_name") or payload.get("event") or payload.get("type") or "manual"
                session = args.session or infer_session(args.agent, payload, os.getcwd())
                text = args.text or infer_text(event, payload)
                if not args.state and should_ignore_event(args.agent, event, payload, text):
                    append_hook_log(args.agent, event, session, "ignored")
                    result = {"ok": True, "ignored": True, "event": event, "session": session}
                else:
                    state = args.state or event_to_state(args.agent, event, payload)
                    append_hook_log(args.agent, event, session, state)
                    source = "{}:{}".format(args.agent, event)
                    if (
                        args.agent in ("codex", "claude")
                        and event in TERMINAL_EVENTS
                        and not args.session
                        and not payload_has_session(payload)
                    ):
                        result = runtime.clear_sessions_by_prefix(
                            "{}:".format(args.agent),
                            source=source,
                            text=text,
                        )
                    else:
                        result = runtime.set_session_state(
                            session=session,
                            state=state,
                            source=source,
                            text=text,
                        )
    except Exception as exc:
        print("signal hook failed: {}".format(exc), file=sys.stderr)
        return 1

    if args.quiet:
        return 0
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        if result.get("session_state"):
            action = result["session_state"]
        elif result.get("ignored"):
            action = "ignored"
        elif args.refresh:
            action = "refresh"
        elif args.clear:
            action = "clear"
        else:
            action = "configure"
        print("{} -> {}".format(action, result.get("aggregate_state", "ok")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
