"""Human-scale tickets + snapshot export.

Tickets are the human-scale layer (tasks, questions, decisions) — the
things a person tracks in an issue tracker. They live in a small local
store here so the reference implementation runs with zero services;
in production this maps 1:1 onto a local tracker's API (e.g. Gitea).

The snapshot is the contract that keeps tracker state honest inside a
file-based system: full state is exported back into the repository as
JSON + a human-readable page, so session boot, backup and audit all
read files, not a service.
"""
from __future__ import annotations

import json
import os
import time

TICKET_STATUSES = ("open", "in_progress", "waiting_decision", "closed")
CLOSE_REASONS = ("proven", "refuted", "split", "done", "dropped")


class Tickets:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            self._save([])

    def _load(self) -> list[dict]:
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self, rows: list[dict]) -> None:
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def new(self, title: str, owner: str = "", decider: str = "",
            next_trigger: str = "", ref: str = "") -> dict:
        rows = self._load()
        row = {"id": len(rows) + 1, "title": title, "owner": owner,
               "decider": decider, "next_trigger": next_trigger,
               "ref": ref, "status": "open", "created": time.time(),
               "history": [{"ts": time.time(), "event": "created"}]}
        if decider:
            row["status"] = "waiting_decision"
        rows.append(row)
        self._save(rows)
        return row

    def set_status(self, ticket_id: int, status: str, by: str,
                   reason: str = "") -> dict:
        if status not in TICKET_STATUSES:
            raise ValueError(f"illegal ticket status {status!r}")
        if status == "closed" and reason and reason not in CLOSE_REASONS:
            raise ValueError(f"illegal close reason {reason!r}")
        rows = self._load()
        for row in rows:
            if row["id"] == ticket_id:
                row["status"] = status
                row.setdefault("history", []).append(
                    {"ts": time.time(), "event": f"{status} by {by}",
                     "reason": reason})
                self._save(rows)
                return row
        raise KeyError(ticket_id)

    def comment(self, ticket_id: int, by: str, text: str) -> dict:
        rows = self._load()
        for row in rows:
            if row["id"] == ticket_id:
                row.setdefault("history", []).append(
                    {"ts": time.time(), "event": f"comment by {by}",
                     "reason": text})
                self._save(rows)
                return row
        raise KeyError(ticket_id)

    def all(self) -> list[dict]:
        return self._load()

    def decision_queue(self) -> list[dict]:
        return [r for r in self._load()
                if r["status"] == "waiting_decision"]


def export_snapshot(board, tickets: Tickets, out_dir: str) -> dict:
    """Write snapshot.json + snapshot.md; returns the snapshot dict."""
    os.makedirs(out_dir, exist_ok=True)
    leaves = board.leaves()
    snap = {
        "generated_at": time.time(),
        "leaves": leaves,
        "tickets": tickets.all(),
        "decision_queue": tickets.decision_queue(),
        "counts": {
            "leaves_open": sum(1 for l in leaves.values() if l["status"] == "open"),
            "leaves_closed": sum(1 for l in leaves.values() if l["status"] == "closed"),
            "tickets_open": sum(1 for t in tickets.all() if t["status"] != "closed"),
        },
    }
    with open(os.path.join(out_dir, "snapshot.json"), "w", encoding="utf-8") as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)
    lines = ["# Snapshot", "",
             f"leaves: {snap['counts']['leaves_closed']} closed / "
             f"{snap['counts']['leaves_open']} open; "
             f"tickets open: {snap['counts']['tickets_open']}", "",
             "## Waiting for a decision", ""]
    for t in snap["decision_queue"]:
        lines.append(f"- #{t['id']} {t['title']} "
                     f"(decider: {t['decider']}, next: {t['next_trigger']})")
    lines += ["", "## Leaves", ""]
    for lid, leaf in sorted(leaves.items()):
        extra = leaf.get("outcome", leaf["status"])
        lines.append(f"- {lid}: {extra} — {leaf.get('task', '')[:80]}")
    with open(os.path.join(out_dir, "snapshot.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return snap
