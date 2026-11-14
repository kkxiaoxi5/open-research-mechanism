#!/usr/bin/env python3
"""认领板（Claim Board）最小参考实现。

设计要点（对应 docs/03-workflow.md）：
- 只追加的 JSONL 事件日志；写入用文件锁串行化，避免并发写坏。
- 结局只有三值：proven（证成）/ refuted（证否）/ split（拆小）。
  试图以其他结局关单（例如 "unknown" / "判不出"）会被拒绝。
- 以 split 关单时必须给出子题；以任何方式标记卡住时必须写卡点并生成子题。

用法：
    python claimboard.py --board board.jsonl open  --id A-001 --by lead \
        --title "……" --prediction "……" --acceptance "已知答案逐位复现"
    python claimboard.py --board board.jsonl claim --id A-001 --by worker-1
    python claimboard.py --board board.jsonl deliver --id A-001 --by worker-1 \
        --result "……" --changed "改变了判断：……"
    python claimboard.py --board board.jsonl close --id A-001 --by reviewer \
        --outcome split --children A-002 A-003
    python claimboard.py --board board.jsonl table
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone

OUTCOMES = ("proven", "refuted", "split")
EVENTS = ("open", "claim", "deliver", "accept", "reject", "close", "note")


def _lock_path(board: str) -> str:
    return board + ".lock"


def _acquire_lock(board: str):
    """简易自旋文件锁（跨平台够用；生产环境可换成 OS 级文件锁）。"""
    import time

    lock = _lock_path(board)
    for _ in range(200):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            return fd, lock
        except FileExistsError:
            time.sleep(0.05)
    raise TimeoutError(f"cannot acquire board lock: {lock}")


def _release_lock(fd, lock: str) -> None:
    try:
        os.close(fd)
    finally:
        try:
            os.unlink(lock)
        except FileNotFoundError:
            pass


def append_event(board: str, event: dict) -> dict:
    event = dict(event)
    event.setdefault("ts", datetime.now(timezone.utc).isoformat())
    fd, lock = _acquire_lock(board)
    try:
        with open(board, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
            f.flush()
            os.fsync(f.fileno())
    finally:
        _release_lock(fd, lock)
    return event


def read_events(board: str) -> list[dict]:
    if not os.path.exists(board):
        return []
    out = []
    with open(board, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def fold_state(events: list[dict]) -> dict[str, dict]:
    """把事件流折叠成每张卡的当前状态。"""
    cards: dict[str, dict] = {}
    for e in events:
        cid = e.get("id")
        if not cid:
            continue
        card = cards.setdefault(cid, {"id": cid, "status": "unknown", "history": []})
        card["history"].append(e)
        kind = e["event"]
        if kind == "open":
            card.update(status="open", title=e.get("title"), owner=None)
        elif kind == "claim":
            card.update(status="claimed", owner=e.get("by"))
        elif kind == "deliver":
            card.update(status="delivered", result=e.get("result"),
                        changed=e.get("changed"))
        elif kind == "accept":
            card["status"] = "accepted"
        elif kind == "reject":
            card["status"] = "rejected"
        elif kind == "close":
            card.update(status="closed", outcome=e.get("outcome"),
                        children=e.get("children", []))
    return cards


def require(cond: bool, msg: str) -> None:
    if not cond:
        print(f"error: {msg}", file=sys.stderr)
        raise SystemExit(2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Claim Board (reference implementation)")
    p.add_argument("--board", default="board.jsonl")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("open")
    sp.add_argument("--id", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--title", required=True)
    sp.add_argument("--prediction", required=True, help="事前预测（必填）")
    sp.add_argument("--acceptance", required=True, help="验收方法（必填）")
    sp.add_argument("--source", default="", help="出处：命题/原话/上级卡号")

    for name in ("claim", "accept", "reject"):
        sp = sub.add_parser(name)
        sp.add_argument("--id", required=True)
        sp.add_argument("--by", required=True)

    sp = sub.add_parser("deliver")
    sp.add_argument("--id", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--result", required=True)
    sp.add_argument("--changed", required=True, help="哪个判断因此改变了（必填）")

    sp = sub.add_parser("close")
    sp.add_argument("--id", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--outcome", required=True,
                    help="只能是 proven / refuted / split")
    sp.add_argument("--children", nargs="*", default=[],
                    help="outcome=split 时必填：拆出的子题卡号")
    sp.add_argument("--stuck", default="",
                    help="卡点（不超过三句）；填写时必须同时给出 --children")

    sp = sub.add_parser("note")
    sp.add_argument("--id", required=True)
    sp.add_argument("--by", required=True)
    sp.add_argument("--text", required=True)

    sub.add_parser("table")

    args = p.parse_args(argv)
    cards = fold_state(read_events(args.board))

    if args.cmd == "open":
        require(args.id not in cards, f"card already exists: {args.id}")
        append_event(args.board, {
            "event": "open", "id": args.id, "by": args.by, "title": args.title,
            "prediction": args.prediction, "acceptance": args.acceptance,
            "source": args.source,
        })
    elif args.cmd in ("claim", "accept", "reject"):
        require(args.id in cards, f"unknown card: {args.id}")
        append_event(args.board, {"event": args.cmd, "id": args.id, "by": args.by})
    elif args.cmd == "deliver":
        require(args.id in cards, f"unknown card: {args.id}")
        append_event(args.board, {
            "event": "deliver", "id": args.id, "by": args.by,
            "result": args.result, "changed": args.changed,
        })
    elif args.cmd == "close":
        require(args.id in cards, f"unknown card: {args.id}")
        require(args.outcome in OUTCOMES,
                f"illegal outcome {args.outcome!r}: only {OUTCOMES} are allowed; "
                "'cannot decide' is not a legal outcome — split the card instead")
        if args.outcome == "split":
            require(bool(args.children),
                    "outcome=split requires --children (the smaller cards)")
        if args.stuck:
            require(bool(args.children),
                    "a stuck card must spawn a different-angle child card "
                    "(--children); waiting without a child is not allowed")
        append_event(args.board, {
            "event": "close", "id": args.id, "by": args.by,
            "outcome": args.outcome, "children": args.children,
            "stuck": args.stuck,
        })
    elif args.cmd == "note":
        append_event(args.board, {
            "event": "note", "id": args.id, "by": args.by, "text": args.text,
        })
    elif args.cmd == "table":
        for cid in sorted(cards):
            c = cards[cid]
            extra = f" outcome={c['outcome']}" if c.get("outcome") else ""
            print(f"{cid}\t{c['status']}{extra}\t{c.get('title') or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
