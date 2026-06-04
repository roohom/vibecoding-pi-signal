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
from ..states import AGENT_EVENT_MAPS


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
    for key in ("session_id", "sessionId", "conversation_id", "conversationId", "cwd"):
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
    return mapping.get(event, "working")


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
                state = args.state or event_to_state(args.agent, event, payload)
                session = args.session or infer_session(args.agent, payload, os.getcwd())
                text = args.text or infer_text(event, payload)
                append_hook_log(args.agent, event, session, state)
                result = runtime.set_session_state(
                    session=session,
                    state=state,
                    source="{}:{}".format(args.agent, event),
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
        action = result.get("session_state") or ("refresh" if args.refresh else "clear" if args.clear else "configure")
        print("{} -> {}".format(action, result.get("aggregate_state", "ok")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
