"""Pluggable model backends.

A backend is any object with `complete(system, user) -> str`.
Two are provided:

- MockBackend: deterministic canned answers keyed by a marker in the
  prompt. Runs the whole loop with no keys at all; exists so the demo
  and the tests prove the *mechanism*, not a model's intelligence.
- OpenAICompatBackend: talks to any OpenAI-compatible chat endpoint
  using only the standard library. Point it at a public API or an
  intranet model server via environment variables:
    MECH_AGENT_BASE_URL, MECH_AGENT_API_KEY, MECH_AGENT_MODEL
"""
from __future__ import annotations

import json
import os
import urllib.request


class MockBackend:
    """Canned answers: the prompt must contain `MOCK:<key>`; the table
    maps keys to replies. Unknown keys get a split request, which is the
    honest default for a model that cannot answer."""

    def __init__(self, table: dict[str, str] | None = None):
        self.table = table or {}

    def complete(self, system: str, user: str) -> str:
        for key, reply in self.table.items():
            if f"MOCK:{key}" in user:
                return reply
        return "SPLIT"


class OpenAICompatBackend:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None, timeout: float = 120):
        self.base_url = (base_url or os.environ.get("MECH_AGENT_BASE_URL", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("MECH_AGENT_API_KEY", "")
        self.model = model or os.environ.get("MECH_AGENT_MODEL", "")
        self.timeout = timeout
        if not self.base_url or not self.model:
            raise ValueError("set MECH_AGENT_BASE_URL and MECH_AGENT_MODEL")

    def complete(self, system: str, user: str) -> str:
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": 0,
        }).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


def backend_from_env(mock_table: dict[str, str] | None = None):
    if os.environ.get("MECH_AGENT_BASE_URL"):
        return OpenAICompatBackend()
    return MockBackend(mock_table)
