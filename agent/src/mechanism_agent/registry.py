"""Agent registry: who exists, what role, which model.

The roster is data, not code: the user adds/removes agents and sets
each agent's model parameters from the console, and the orchestrator
builds its workers from this registry on every cycle. API keys are
never stored — an agent names the *environment variable* that holds
its key, and the key is read from the server's environment at use.
"""
from __future__ import annotations

import json
import os

from .backend import MockBackend, OpenAICompatBackend

ROLES = ("coordinator", "worker", "reviewer")

DEFAULT_AGENTS = [
    {"name": "coordinator", "role": "coordinator"},
    {"name": "worker-1", "role": "worker"},
    {"name": "worker-2", "role": "worker"},
    {"name": "reviewer-1", "role": "reviewer"},
]

_FIELDS = {"model": "", "base_url": "", "api_key_env": "",
           "temperature": 0.0, "enabled": True}


def _normalise(rec: dict) -> dict:
    out = {"name": str(rec["name"]).strip(),
           "role": rec.get("role", "worker")}
    if not out["name"]:
        raise ValueError("agent name must not be empty")
    if out["role"] not in ROLES:
        raise ValueError(f"illegal role {out['role']!r}: one of {ROLES}")
    for key, default in _FIELDS.items():
        out[key] = rec.get(key, default)
    out["temperature"] = float(out["temperature"])
    out["enabled"] = bool(out["enabled"])
    return out


class AgentsStore:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            self._save([_normalise(a) for a in DEFAULT_AGENTS])

    def _load(self) -> list[dict]:
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, rows: list[dict]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def all(self) -> list[dict]:
        return self._load()

    def get(self, name: str) -> dict | None:
        for row in self._load():
            if row["name"] == name:
                return row
        return None

    def upsert(self, rec: dict) -> dict:
        rec = _normalise(rec)
        rows = [r for r in self._load() if r["name"] != rec["name"]]
        rows.append(rec)
        rows.sort(key=lambda r: (ROLES.index(r["role"]), r["name"]))
        self._save(rows)
        return rec

    def remove(self, name: str) -> None:
        rows = self._load()
        kept = [r for r in rows if r["name"] != name]
        if len(kept) == len(rows):
            raise KeyError(name)
        self._save(kept)

    def workers(self) -> list[dict]:
        return [r for r in self._load()
                if r["role"] == "worker" and r["enabled"]]

    def reviewer(self) -> dict | None:
        for r in self._load():
            if r["role"] == "reviewer" and r["enabled"]:
                return r
        return None


def backend_for(agent: dict, mock_table: dict | None = None):
    """Build the backend one agent runs on, from its registry entry."""
    base_url = agent.get("base_url") or os.environ.get("MECH_AGENT_BASE_URL", "")
    model = agent.get("model") or os.environ.get("MECH_AGENT_MODEL", "")
    if base_url and model:
        key_env = agent.get("api_key_env") or "MECH_AGENT_API_KEY"
        return OpenAICompatBackend(
            base_url=base_url, model=model,
            api_key=os.environ.get(key_env, ""),
            temperature=float(agent.get("temperature", 0.0)))
    return MockBackend(mock_table)
