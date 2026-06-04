#!/usr/bin/env python3
"""Send a signal state to the Raspberry Pi LED ring service."""

import argparse
import json
import sys
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from vibecoding_pi_signal.client import SignalClient
from vibecoding_pi_signal.config import load_config
from vibecoding_pi_signal.states import VALID_STATES


def main():
    config = load_config()
    parser = argparse.ArgumentParser()
    parser.add_argument("state", choices=sorted(VALID_STATES))
    parser.add_argument("--host", default=config.host)
    parser.add_argument("--port", type=int, default=config.port)
    parser.add_argument("--source", default="manual")
    parser.add_argument("--session", default="default")
    parser.add_argument("--text", default="")
    args = parser.parse_args()

    try:
        result = SignalClient(args.host, args.port, timeout=5).post_state(
            args.state,
            source=args.source,
            session=args.session,
            text=args.text,
        )
    except urllib.error.URLError as exc:
        print("failed to send signal: {}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
