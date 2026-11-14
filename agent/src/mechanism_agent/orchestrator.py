"""The orchestrator: one wake-up cycle.

Each cycle is deliberately boring and fully logged in the board itself:
  1. reconcile  — expired leases go back to open; stuck leaves are
                  closed as "split" by the reviewer and replaced with
                  different-angle children (never left hanging);
  2. dispatch   — open leaves are claimed by workers and answered;
  3. review     — delivered leaves are recomputed by the reviewer and
                  closed proven / refuted / split;
  4. snapshot   — full state is exported back into files.

The orchestrator never grades its own dispatch and never closes a leaf
it delivered: closing belongs to the reviewer.
"""
from __future__ import annotations

from .agents import Reviewer, Worker
from .tracker import export_snapshot


class Orchestrator:
    def __init__(self, board, tickets, workers: list[Worker],
                 reviewer: Reviewer, snapshot_dir: str):
        self.board = board
        self.tickets = tickets
        self.workers = workers
        self.reviewer = reviewer
        self.snapshot_dir = snapshot_dir
        self._wi = 0

    def _spawn_children(self, leaf: dict) -> None:
        spec = (leaf.get("checker_args") or {}).get("split_into")
        children = spec or [{
            "suffix": "retry",
            "task": leaf["task"] + " (re-asked from a different angle)",
            "checker": leaf.get("checker"),
            "checker_args": {k: v for k, v in (leaf.get("checker_args") or {}).items()
                             if k != "split_into"},
        }]
        for child in children:
            cid = f"{leaf['leaf_id']}.{child['suffix']}"
            if cid not in self.board.leaves():
                self.board.open_leaf(cid, child["task"], child.get("checker"),
                                     child.get("checker_args") or {},
                                     parent=leaf["leaf_id"],
                                     evidence=leaf.get("evidence", "exploratory"))

    def _handle_stuck(self) -> int:
        acted = 0
        for leaf in self.board.leaves().values():
            if leaf["status"] == "claimed" and leaf.get("stuck_notes"):
                self.board.close(leaf["leaf_id"], self.reviewer.name, "split",
                                 "worker reported stuck; split into children")
                self._spawn_children(leaf)
                acted += 1
        return acted

    def cycle(self, max_rounds: int = 20) -> dict:
        released = self.board.release_expired()
        log = {"released": released, "proven": 0, "refuted": 0, "split": 0}
        for _ in range(max_rounds):
            splits = self._handle_stuck()
            log["split"] = log.get("split", 0) + splits
            progress = splits > 0
            leaves = self.board.leaves()
            for leaf in leaves.values():
                if leaf["status"] != "open":
                    continue
                worker = self.workers[self._wi % len(self.workers)]
                self._wi += 1
                self.board.claim(leaf["leaf_id"], worker.name)
                worker.work(self.board, leaf)
                progress = True
            for leaf in self.board.leaves().values():
                if leaf["status"] == "delivered":
                    outcome = self.reviewer.review(self.board, leaf)
                    log[outcome] = log.get(outcome, 0) + 1
                    progress = True
            if not progress:
                break
        snap = export_snapshot(self.board, self.tickets, self.snapshot_dir)
        log["counts"] = snap["counts"]
        return log
