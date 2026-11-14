"""Command line: init / seed-demo / run / snapshot / serve.

State lives in one directory (default ./mech-state):
  board.jsonl   — the claim board (append-only truth)
  tickets.json  — human-scale tickets
  snapshot/     — exported state (snapshot.json + snapshot.md)

The demo seeds three leaves chosen so one orchestrator cycle exercises
all three closing outcomes with the mock backend (no keys needed):
  D1 answered correctly  -> proven
  D2 answered wrongly    -> refuted (the reviewer recomputes; it does
                            not trust the worker)
  D3 not answerable as   -> split into D3.a / D3.b, which then close
  stated                    proven
"""
from __future__ import annotations

import argparse
import json
import os

from .agents import Reviewer, Worker
from .backend import MockBackend, backend_from_env
from .board import Board
from .orchestrator import Orchestrator
from .tracker import Tickets, export_snapshot

DEMO_MOCK = {"D1": "5050", "D2": "300", "D3.a": "55", "D3.b": "30"}


def _paths(home: str) -> dict:
    return {"board": os.path.join(home, "board.jsonl"),
            "tickets": os.path.join(home, "tickets.json"),
            "snapshot": os.path.join(home, "snapshot")}


def cmd_init(home: str) -> None:
    os.makedirs(home, exist_ok=True)
    p = _paths(home)
    Board(p["board"])
    Tickets(p["tickets"])
    print(f"initialised state in {home}")


def cmd_seed_demo(home: str) -> None:
    p = _paths(home)
    board, tickets = Board(p["board"]), Tickets(p["tickets"])
    board.open_leaf("D1", "Sum of the integers from 1 to 100",
                    "sum_to_n", {"n": 100})
    board.open_leaf("D2", "Product of the first 5 prime numbers",
                    "prime_product", {"k": 5})
    board.open_leaf("D3", "Give one number that is both the sum 1..10 "
                          "and the product of the first 3 primes",
                    None, {"split_into": [
                        {"suffix": "a", "task": "Sum of the integers from 1 to 10",
                         "checker": "sum_to_n", "checker_args": {"n": 10}},
                        {"suffix": "b", "task": "Product of the first 3 prime numbers",
                         "checker": "prime_product", "checker_args": {"k": 3}},
                    ]})
    tickets.new("Review the demo results", owner="lead")
    tickets.new("Decide whether to adopt the tracker pilot",
                decider="user", next_trigger="pilot reconciliation day")
    print("seeded demo leaves D1, D2, D3 and two tickets")


def cmd_run(home: str) -> None:
    p = _paths(home)
    board, tickets = Board(p["board"]), Tickets(p["tickets"])
    backend = backend_from_env(DEMO_MOCK)
    from .skills import prompt_block
    orch = Orchestrator(board, tickets,
                        workers=[Worker("worker-1", backend, prompt_block("worker")),
                                 Worker("worker-2", backend, prompt_block("worker"))],
                        reviewer=Reviewer("reviewer-1"),
                        snapshot_dir=p["snapshot"])
    print(json.dumps(orch.cycle(), ensure_ascii=False, indent=1))


def cmd_snapshot(home: str) -> None:
    p = _paths(home)
    snap = export_snapshot(Board(p["board"]), Tickets(p["tickets"]), p["snapshot"])
    print(json.dumps(snap["counts"], ensure_ascii=False))


def cmd_skills() -> None:
    from .skills import discover
    for s in discover():
        print(f"{s['name']}: {s['description']} "
              f"[roles: {', '.join(s.get('roles', []))}]")


def cmd_serve(home: str, port: int) -> None:
    from .dashboard import serve
    print(f"dashboard on http://127.0.0.1:{port} (read-only)")
    serve(_paths(home)["snapshot"], port=port)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="mechanism-agent")
    ap.add_argument("--home", default=os.environ.get("MECH_HOME", "./mech-state"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    sub.add_parser("seed-demo")
    sub.add_parser("run")
    sub.add_parser("snapshot")
    sub.add_parser("skills")
    sv = sub.add_parser("serve")
    sv.add_argument("--port", type=int, default=8765)
    args = ap.parse_args(argv)
    if args.cmd == "init":
        cmd_init(args.home)
    elif args.cmd == "seed-demo":
        cmd_seed_demo(args.home)
    elif args.cmd == "run":
        cmd_run(args.home)
    elif args.cmd == "snapshot":
        cmd_snapshot(args.home)
    elif args.cmd == "skills":
        cmd_skills()
    elif args.cmd == "serve":
        cmd_serve(args.home, args.port)


if __name__ == "__main__":
    main()
