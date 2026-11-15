"""Conversation log: persistent, branchable chat.

Every channel ("all" plus one per agent) is an append-only log of
messages. Each message carries a parent_id, so a conversation is a
tree, not a line: posting with parent_id set to an older message
forks a new branch from that point (the UI's prompt navigator picks
the position). History is never rewritten — a fork adds a branch,
the original line stays.

Broadcasts (channel "all") appear in every thread; a member channel
shows its own messages plus broadcasts.
"""
from __future__ import annotations

import json
import os
import time


class ChatLog:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    def post(self, channel: str, author: str, text: str,
             parent_id: int | None = None, kind: str = "chat") -> dict:
        rows = self.all()
        rec = {"id": (rows[-1]["id"] + 1) if rows else 1,
               "ts": time.time(), "channel": channel, "author": author,
               "text": text, "parent_id": parent_id, "kind": kind}
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def all(self) -> list[dict]:
        out = []
        if os.path.exists(self.path):
            with open(self.path, encoding="utf-8") as fh:
                for line in fh:
                    if line.strip():
                        out.append(json.loads(line))
        return out

    def thread(self, channel: str) -> list[dict]:
        return [m for m in self.all()
                if m["channel"] in (channel, "all")]

    def unanswered(self, channel: str, agent: str | None = None) -> list[dict]:
        """User messages in a channel after that agent's own last reply
        in the same channel (broadcasts and other agents don't count)."""
        agent = agent or channel
        last_reply = 0
        for m in self.all():
            if m["channel"] == channel and m["author"] == agent:
                last_reply = max(last_reply, m["id"])
        return [m for m in self.all()
                if m["channel"] == channel and m["author"] == "user"
                and m["id"] > last_reply]
