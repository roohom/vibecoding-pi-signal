"""HTTP client for the Raspberry Pi signal server."""

import json
import urllib.request
from .states import VALID_STATES

class SignalClient:
    def __init__(self, host, port=8765, timeout=3):
        self.host = host
        self.port = int(port)
        self.timeout = timeout

    def url(self, path):
        return "http://{}:{}{}".format(self.host, self.port, path)

    def post_state(self, state, source="", session="", text=""):
        if state not in VALID_STATES:
            raise ValueError("unknown state: {}".format(state))
        data = json.dumps({"state": state, "source": source, "session": session, "text": text}).encode("utf-8")
        request = urllib.request.Request(self.url("/signal"), data=data, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8") or "{}")

    def health(self):
        with urllib.request.urlopen(self.url("/health"), timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
