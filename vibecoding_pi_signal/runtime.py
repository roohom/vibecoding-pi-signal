"""Session-aware state aggregation for agent hooks."""

import json
import os
import time
from pathlib import Path

from .client import SignalClient
from .config import load_config
from .states import (
    ACTIVE_SESSION_SECONDS,
    EPHEMERAL_SECONDS,
    PRIORITY,
    STALE_SESSION_SECONDS,
    VALID_STATES,
    is_codex_background_text,
)


class SessionStore:
    def __init__(self, path):
        self.path = Path(path).expanduser()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data.get("sessions", {}) if isinstance(data, dict) else {}

    def save(self, sessions):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_name(self.path.name + ".tmp")
        tmp_path.write_text(
            json.dumps({"sessions": sessions}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(str(tmp_path), str(self.path))


class SignalRuntime:
    def __init__(self, client=None, store=None, config=None):
        self.config = config or load_config()
        self.client = client or SignalClient(self.config.host, self.config.port)
        self.store = store or SessionStore(Path(self.config.state_dir) / "sessions.json")

    def prune_sessions(self, sessions, now=None):
        now = now or time.time()
        pruned = {}
        for session, item in sessions.items():
            if self.should_ignore_stored_session(session, item):
                continue
            state = item.get("state", "idle")
            if now - item.get("updated_at", 0) > STALE_SESSION_SECONDS:
                continue
            active_ttl = ACTIVE_SESSION_SECONDS.get(state)
            if active_ttl is not None and now - item.get("updated_at", 0) > active_ttl:
                continue
            ttl = EPHEMERAL_SECONDS.get(state)
            if ttl is not None and now - item.get("updated_at", 0) > ttl:
                continue
            if state != "off":
                pruned[session] = item
        return pruned

    def should_ignore_stored_session(self, session, item):
        source = item.get("source", "")
        if not session.startswith("codex:") and not source.startswith("codex:"):
            return False
        return is_codex_background_text(item.get("text", ""))

    def aggregate_state(self, sessions):
        if not sessions:
            return "idle", {}

        winner_session = None
        winner = None
        for session, item in sessions.items():
            state = item.get("state", "idle")
            if state not in PRIORITY:
                state = "idle"
            candidate = (PRIORITY[state], item.get("updated_at", 0), session)
            if winner is None or candidate > winner:
                winner = candidate
                winner_session = session

        item = dict(sessions[winner_session])
        item["session"] = winner_session
        return item.get("state", "idle"), item

    def set_session_state(self, session, state, source, text=""):
        if state not in VALID_STATES:
            raise ValueError("unknown state: {}".format(state))

        sessions = self.prune_sessions(self.store.load())
        if state in ("off", "idle"):
            sessions.pop(session, None)
        else:
            sessions[session] = {
                "state": state,
                "source": source,
                "text": text,
                "updated_at": time.time(),
            }

        aggregate, meta = self.aggregate_state(sessions)
        self.store.save(sessions)
        response = self.client.post_state(
            aggregate,
            source=source,
            session=meta.get("session", session),
            text=text,
        )
        return {
            "ok": True,
            "session_state": state,
            "aggregate_state": aggregate,
            "sessions": sessions,
            "response": response,
        }

    def clear_sessions_by_prefix(self, prefix, source="runtime", text=""):
        sessions = self.prune_sessions(self.store.load())
        sessions = {
            session: item
            for session, item in sessions.items()
            if not session.startswith(prefix)
        }
        aggregate, meta = self.aggregate_state(sessions)
        self.store.save(sessions)
        response = self.client.post_state(
            aggregate,
            source=source,
            session=meta.get("session", prefix + "*"),
            text=text,
        )
        return {
            "ok": True,
            "session_state": "idle",
            "aggregate_state": aggregate,
            "sessions": sessions,
            "response": response,
        }

    def clear_all(self):
        self.store.save({})
        response = self.client.post_state("idle", source="runtime", session="all", text="")
        return {"ok": True, "aggregate_state": "idle", "response": response}

    def refresh(self):
        sessions = self.prune_sessions(self.store.load())
        aggregate, meta = self.aggregate_state(sessions)
        self.store.save(sessions)
        response = self.client.post_state(
            aggregate,
            source="runtime:refresh",
            session=meta.get("session", "aggregate"),
            text=meta.get("text", ""),
        )
        return {
            "ok": True,
            "aggregate_state": aggregate,
            "sessions": sessions,
            "response": response,
        }


def set_session_state(session, state, source, text="", host=None, port=None):
    config = load_config()
    client = SignalClient(host or config.host, port or config.port)
    return SignalRuntime(client=client, config=config).set_session_state(session, state, source, text)


def clear_all(host=None, port=None):
    config = load_config()
    client = SignalClient(host or config.host, port or config.port)
    return SignalRuntime(client=client, config=config).clear_all()


def refresh(host=None, port=None):
    config = load_config()
    client = SignalClient(host or config.host, port or config.port)
    return SignalRuntime(client=client, config=config).refresh()
