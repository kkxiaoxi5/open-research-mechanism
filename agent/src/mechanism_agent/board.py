"""Append-only claim board (JSONL + file lock).

One leaf = one hard sub-problem small enough to be graded by a checker.
Outcomes are exactly three: "proven" / "refuted" / "split".
There is deliberately no "unknown" outcome: a worker who is stuck must
write a short stuck note and the orchestrator spawns a different-angle
child leaf instead of closing the parent as undecided.

State is derived by replaying the JSONL log, so the log is the truth and
any snapshot is a cache. All writes go through one locked append.
"""
from __future__ import annotations

import json
import os
import time
import uuid

try:  # POSIX file lock
    import fcntl

    def _lock(fh) -> None:
        fcntl.flock(fh, fcntl.LOCK_EX)

    def _unlock(fh) -> None:
        fcntl.flock(fh, fcntl.LOCK_UN)

except ImportError:  # Windows file lock
    import msvcrt

    def _lock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_LOCK, 1)

    def _unlock(fh) -> None:
        fh.seek(0)
        msvcrt.locking(fh.fileno(), msvcrt.LK_UNLCK, 1)

OUTCOMES = ("proven", "refuted", "split")
STATUSES = ("open", "claimed", "delivered", "closed")


def _now() -> float:
    return time.time()


class Board:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    # -- low level -----------------------------------------------------
    def _append(self, record: dict) -> dict:
        record = dict(record)
        record.setdefault("ts", _now())
        record.setdefault("rid", uuid.uuid4().hex[:12])
        with open(self.path, "a+", encoding="utf-8") as fh:
            _lock(fh)
            try:
                fh.write(json.dumps(record, ensure_ascii=False) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            finally:
                _unlock(fh)
        return record

    def _events(self) -> list[dict]:
        out = []
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    # -- derived state ---------------------------------------------------
    def leaves(self) -> dict[str, dict]:
        """Replay the log into current leaf states."""
        state: dict[str, dict] = {}
        for ev in self._events():
            kind = ev.get("kind")
            leaf = state.setdefault(ev["leaf_id"], {"leaf_id": ev["leaf_id"]})
            if kind == "open":
                leaf.update(status="open", task=ev["task"],
                            checker=ev.get("checker"),
                            checker_args=ev.get("checker_args", {}),
                            parent=ev.get("parent"),
                            evidence=ev.get("evidence", "exploratory"))
            elif kind == "claim":
                leaf.update(status="claimed", claimed_by=ev["by"],
                            lease_until=ev["lease_until"])
            elif kind == "release":
                leaf.update(status="open")
                leaf.pop("claimed_by", None)
            elif kind == "deliver":
                leaf.update(status="delivered", delivered_by=ev["by"],
                            answer=ev["answer"])
            elif kind == "stuck":
                leaf.setdefault("stuck_notes", []).append(
                    {"by": ev["by"], "note": ev["note"]})
            elif kind == "close":
                leaf.update(status="closed", outcome=ev["outcome"],
                            closed_by=ev["by"], verdict=ev.get("verdict", ""))
        return state

    # -- operations ------------------------------------------------------
    def open_leaf(self, leaf_id: str, task: str, checker: str | None = None,
                  checker_args: dict | None = None, parent: str | None = None,
                  evidence: str = "exploratory") -> dict:
        return self._append({"kind": "open", "leaf_id": leaf_id, "task": task,
                             "checker": checker, "checker_args": checker_args or {},
                             "parent": parent, "evidence": evidence})

    def claim(self, leaf_id: str, by: str, lease_seconds: float = 3600) -> dict:
        leaf = self.leaves().get(leaf_id)
        if not leaf or leaf["status"] != "open":
            raise ValueError(f"leaf {leaf_id} is not open")
        return self._append({"kind": "claim", "leaf_id": leaf_id, "by": by,
                             "lease_until": _now() + lease_seconds})

    def deliver(self, leaf_id: str, by: str, answer: str) -> dict:
        leaf = self.leaves().get(leaf_id)
        if not leaf or leaf["status"] != "claimed" or leaf.get("claimed_by") != by:
            raise ValueError(f"leaf {leaf_id} is not claimed by {by}")
        return self._append({"kind": "deliver", "leaf_id": leaf_id,
                             "by": by, "answer": answer})

    def stuck(self, leaf_id: str, by: str, note: str) -> dict:
        if len(note.strip()) < 10:
            raise ValueError("stuck note too short: say what was tried and what blocks you")
        return self._append({"kind": "stuck", "leaf_id": leaf_id,
                             "by": by, "note": note})

    def release_expired(self) -> list[str]:
        """Orchestrator reconciliation: expired leases return to open."""
        released = []
        for leaf_id, leaf in self.leaves().items():
            if leaf["status"] == "claimed" and leaf.get("lease_until", 0) < _now():
                self._append({"kind": "release", "leaf_id": leaf_id,
                              "by": "orchestrator"})
                released.append(leaf_id)
        return released

    def close(self, leaf_id: str, by: str, outcome: str, verdict: str = "") -> dict:
        if outcome not in OUTCOMES:
            raise ValueError(
                f"illegal outcome {outcome!r}: must be one of {OUTCOMES}; "
                "'cannot decide' is not a closing state")
        leaf = self.leaves().get(leaf_id)
        if not leaf or leaf["status"] == "closed":
            raise ValueError(f"leaf {leaf_id} cannot be closed")
        if leaf.get("delivered_by") == by:
            raise ValueError("author cannot close their own leaf")
        return self._append({"kind": "close", "leaf_id": leaf_id, "by": by,
                             "outcome": outcome, "verdict": verdict})
