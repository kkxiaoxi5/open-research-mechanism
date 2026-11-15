"""Interactive web console for mechanism-agent.

The user's operating surface (PLAN decision: the UI is a required,
interactive part of the system). A pixel-level imitation of the
Claude Code terminal UI: near-black background, monospace type, a
welcome box with the orange ✻ spark, a transcript instead of chat
bubbles — user lines start with ``>`` on a highlighted bar, tool
calls are ``● Name`` lines with ``⎿`` result connectors (board
events open/claim/deliver/close render exactly this way), an
animated ✻ spinner with a thinking verb while a round runs, a
slash-command popup over the composer, a bordered input box with
``⏵⏵`` mode line and ``? for shortcuts``, and a status line with a
block-character progress meter. Around the transcript: a task
sidebar (decision queue / claim board / tickets / agent management
/ relation graph), a prompt navigator that selects any message as
a fork point, and an EN/JA language toggle in the status line.

Discipline is preserved: the web layer never writes state files
directly. Task actions go through Board / Tickets; agent management
goes through the registry; chat is append-only. Nothing here bypasses
the board's rules (three outcomes, no self-closing). API keys are
never stored: an agent's registry entry names an environment
variable, and the key is read from the server environment at use.

There is no login in this reference build; run it on a trusted local
network only (see PLAN.md).
"""
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__
from .agents import CHECKERS, Reviewer, Worker
from .board import Board
from .chat import ChatLog
from .orchestrator import Orchestrator
from .registry import AgentsStore, backend_for
from .skills import prompt_block
from .tracker import Tickets


class Inbox:
    """User -> member direct messages queued for prompt injection."""

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    def post(self, to: str, text: str) -> dict:
        rec = {"ts": time.time(), "to": to, "text": text, "delivered": False}
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

    def pending_for(self, member: str) -> list[dict]:
        return [m for m in self.all()
                if m["to"] in (member, "*") and not m.get("delivered")]

    def mark_delivered(self, member: str) -> None:
        rows = self.all()
        changed = False
        for m in rows:
            if m["to"] in (member, "*") and not m.get("delivered"):
                m["delivered"] = True
                changed = True
        if changed:
            with open(self.path, "w", encoding="utf-8") as fh:
                for m in rows:
                    fh.write(json.dumps(m, ensure_ascii=False) + "\n")


class App:
    def __init__(self, home: str):
        self.home = home
        self.board = Board(os.path.join(home, "board.jsonl"))
        self.tickets = Tickets(os.path.join(home, "tickets.json"))
        self.inbox = Inbox(os.path.join(home, "inbox.jsonl"))
        self.agents = AgentsStore(os.path.join(home, "agents.json"))
        self.chat = ChatLog(os.path.join(home, "chat.jsonl"))
        self.snapshot_dir = os.path.join(home, "snapshot")

    # -- derived views ---------------------------------------------------
    def _activity(self) -> dict[str, dict]:
        act: dict[str, dict] = {}
        for leaf in self.board.leaves().values():
            for key, field in (("claimed_by", "claimed"),
                               ("delivered_by", "delivered"),
                               ("closed_by", "closed")):
                name = leaf.get(key)
                if name:
                    a = act.setdefault(name, {"claimed": 0, "delivered": 0,
                                              "closed": 0, "last": ""})
                    a[field] += 1
                    a["last"] = f"{field} {leaf['leaf_id']}"
            if leaf["status"] == "claimed":
                a = act.setdefault(leaf["claimed_by"], {})
                a["doing"] = leaf["leaf_id"]
        return act

    def _graph(self, agents: list[dict]) -> dict:
        edges: dict[tuple, int] = {}

        def add(frm, to, kind):
            if frm and to and frm != to:
                edges[(frm, to, kind)] = edges.get((frm, to, kind), 0) + 1

        reviewer = self.agents.reviewer()
        rname = reviewer["name"] if reviewer else "reviewer-1"
        for leaf in self.board.leaves().values():
            add("coordinator", leaf.get("claimed_by"), "dispatch")
            add(leaf.get("delivered_by"), rname, "deliver")
            add(rname, leaf.get("closed_by") if leaf.get("closed_by") == rname
                else None, "close")
        for m in self.chat.all():
            if m["author"] == "user" and m["channel"] != "all":
                add("user", m["channel"], "chat")
            elif m["author"] != "user":
                add(m["author"], "user", "reply")
        nodes = [{"name": "user", "role": "user"}] + [
            {"name": a["name"], "role": a["role"]} for a in agents]
        return {"nodes": nodes,
                "edges": [{"from": f, "to": t, "kind": k, "count": c}
                          for (f, t, k), c in sorted(edges.items())]}

    def state(self) -> dict:
        leaves = self.board.leaves()
        tickets = self.tickets.all()
        act = self._activity()
        agents = []
        for a in self.agents.all():
            live = act.get(a["name"], {})
            agents.append({**a,
                           "state": "Active" if live.get("doing") else "Waiting",
                           "doing": live.get("doing", ""),
                           "stats": {k: live.get(k, 0)
                                     for k in ("claimed", "delivered", "closed")},
                           "last": live.get("last", "")})
        feed = [{"ts": ev.get("ts", 0), "kind": ev.get("kind"),
                 "leaf": ev.get("leaf_id"), "by": ev.get("by"),
                 "outcome": ev.get("outcome")}
                for ev in self.board._events()]
        feed.sort(key=lambda e: e["ts"], reverse=True)
        return {
            "version": __version__,
            "counts": {
                "leaves_open": sum(1 for l in leaves.values()
                                   if l["status"] != "closed"),
                "leaves_closed": sum(1 for l in leaves.values()
                                     if l["status"] == "closed"),
                "tickets_open": sum(1 for t in tickets
                                    if t["status"] != "closed"),
                "decisions": len(self.tickets.decision_queue()),
            },
            "decisions": self.tickets.decision_queue(),
            "leaves": sorted(leaves.values(), key=lambda l: l["leaf_id"]),
            "tickets": tickets,
            "agents": agents,
            "chat": self.chat.all(),
            "graph": self._graph(self.agents.all()),
            "feed": feed[:40],
            "checkers": sorted(CHECKERS),
        }

    # -- task actions ------------------------------------------------------
    def open_leaf(self, data: dict) -> dict:
        checker = data.get("checker") or None
        if checker and checker not in CHECKERS:
            raise ValueError(f"unknown checker {checker!r}")
        args = data.get("checker_args") or {}
        if isinstance(args, str):
            args = json.loads(args) if args.strip() else {}
        leaf_id = (data.get("leaf_id") or "").strip()
        if not leaf_id:
            existing = self.board.leaves()
            n = 1
            while f"L{n}" in existing:
                n += 1
            leaf_id = f"L{n}"
        self.board.open_leaf(leaf_id, data["task"], checker, args)
        return {"leaf_id": leaf_id}

    def open_ticket(self, data: dict) -> dict:
        row = self.tickets.new(data["title"], owner=data.get("owner", ""),
                               decider=data.get("decider", ""),
                               next_trigger=data.get("next_trigger", ""))
        return {"ticket_id": row["id"]}

    def decide(self, data: dict) -> dict:
        tid = int(data["ticket_id"])
        reason = "done" if data.get("decision") == "approve" else "dropped"
        self.tickets.set_status(tid, "closed", by="user", reason=reason)
        note = (data.get("note") or "").strip()
        if note:
            self.tickets.comment(tid, "user", note)
        return {"ticket_id": tid, "closed_as": reason}

    def close_ticket(self, data: dict) -> dict:
        tid = int(data["ticket_id"])
        self.tickets.set_status(tid, "closed", by="user",
                                reason=data.get("reason", "done"))
        return {"ticket_id": tid}

    # -- agent management --------------------------------------------------
    def upsert_agent(self, data: dict) -> dict:
        return self.agents.upsert(data)

    def delete_agent(self, data: dict) -> dict:
        self.agents.remove(data["name"])
        return {"removed": data["name"]}

    # -- chat ----------------------------------------------------------------
    def post_chat(self, data: dict) -> dict:
        channel = data.get("channel", "all")
        rec = self.chat.post(channel, "user", data["text"],
                             parent_id=data.get("parent_id"))
        if channel != "all":
            self.inbox.post(channel, data["text"])
        return rec

    def message(self, data: dict) -> dict:  # legacy direct-message endpoint
        return self.post_chat({"channel": data.get("to", "all"),
                               "text": data["text"]})

    # -- wake-up cycle --------------------------------------------------------
    def run_cycle(self) -> dict:
        from .cli import DEMO_MOCK
        before = len(self.board._events())
        workers = []
        for a in self.agents.workers():
            extra = ""
            pending = self.inbox.pending_for(a["name"])
            if pending:
                extra = "\n\nDirect messages from the user:\n" + "\n".join(
                    f"- {m['text']}" for m in pending)
                self.inbox.mark_delivered(a["name"])
            workers.append(Worker(a["name"], backend_for(a, DEMO_MOCK),
                                  prompt_block("worker") + extra))
        if not workers:
            raise ValueError("no enabled worker agents in the registry")
        rev = self.agents.reviewer()
        orch = Orchestrator(self.board, self.tickets, workers=workers,
                            reviewer=Reviewer(rev["name"] if rev else "reviewer-1"),
                            snapshot_dir=self.snapshot_dir)
        log = orch.cycle()
        self._chat_replies(before)
        return log

    def _chat_replies(self, events_before: int) -> None:
        """After a cycle, agents answer unanswered user chat from what
        they actually did (board events), or via their real backend."""
        new_events = self.board._events()[events_before:]
        did: dict[str, list[str]] = {}
        for ev in new_events:
            by = ev.get("by")
            if by and ev.get("kind") in ("deliver", "close"):
                did.setdefault(by, []).append(
                    f"{ev['kind']} {ev.get('leaf_id', '')}"
                    + (f" → {ev['outcome']}" if ev.get("outcome") else ""))
        coord = self.chat.post(
            "all", "coordinator",
            "Wake-up round complete: " + (", ".join(
                f"{k} ×{len(v)}" for k, v in sorted(did.items()))
                if did else "no new deliveries this round") + ".",
            kind="summary")
        _ = coord
        for a in self.agents.all():
            if a["role"] == "coordinator" or not a["enabled"]:
                continue
            pending = self.chat.unanswered(a["name"])
            if not pending:
                continue
            backend = backend_for(a)
            from .backend import OpenAICompatBackend
            if isinstance(backend, OpenAICompatBackend):
                thread = self.chat.thread(a["name"])[-12:]
                convo = "\n".join(f"{m['author']}: {m['text']}"
                                  for m in thread)
                reply = backend.complete(
                    f"You are {a['name']}, a research agent. Answer the "
                    f"user briefly and concretely.", convo)
            else:
                mine = did.get(a["name"], [])
                reply = ("(demo backend) Received. My work this round: " +
                         ("; ".join(mine) if mine else "no new deliveries") +
                         ". Connect a real model and I will answer directly.")
            self.chat.post(a["name"], a["name"], reply,
                           parent_id=pending[-1]["id"], kind="reply")

PAGE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mechanism-agent console</title>
<style>
:root{--bg:#0c0c0c;--panel:#0c0c0c;--line:#2b2b2b;--line2:#3d3d3d;
--ink:#d6d6d6;--dim:#9a9a9a;--faint:#636363;--accent:#d97757;
--green:#4caf7d;--red:#e5534b;--amber:#d29922;--blue:#58a6ff;--purple:#b083f0;
--userbg:#232329;
--mono:ui-monospace,"SF Mono",Menlo,"Cascadia Code",Consolas,"Hiragino Sans","Microsoft YaHei",monospace}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);display:grid;
grid-template-columns:296px 1fr 216px;grid-template-rows:1fr 24px;height:100vh;
font:13px/1.55 var(--mono)}
::selection{background:#4a3226}
aside{border-right:1px solid var(--line);overflow-y:auto;padding:10px 12px 16px;grid-row:1}
aside h1{font-size:13px;margin:0;font-weight:700}
aside h1 .spark{color:var(--accent)}
.sub{color:var(--faint);font-size:11px;margin:2px 0 4px}
button{background:none;border:0;color:var(--ink);cursor:pointer;font:inherit;padding:0}
button:hover{color:#fff}
.abtn{color:var(--accent)}
.abtn:hover{color:var(--accent);text-decoration:underline}
.sect{font-size:12px;font-weight:700;color:var(--ink);margin:18px 0 4px}
.sect:first-of-type{margin-top:10px}
.stabs{display:flex;gap:14px;margin:14px 0 2px;border-bottom:1px solid var(--line);padding-bottom:5px}
.stabs button{color:var(--faint)}
.stabs button.on{color:var(--ink);font-weight:700}
.stabs button.on::before{content:"❯ ";color:var(--accent)}
.badge{color:var(--amber);font-weight:700;margin-left:3px}
.trow{padding:3px 0 5px;border-bottom:1px solid #1b1b1b}
.trow .r1{display:flex;gap:7px;align-items:baseline}
.trow .id{color:var(--faint)}
.trow .ttl{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:var(--ink)}
.trow .meta{color:var(--faint);font-size:11.5px;margin-left:15px;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
.sdot{font-size:9px;flex:none}
.proven{color:var(--green)}.refuted{color:var(--red)}.split{color:var(--amber)}
.open{color:#8a8f98}.claimed{color:var(--blue)}.delivered{color:var(--purple)}
.closed{color:#555}
.tag{color:var(--dim);font-size:11px}
.tag::before{content:"("}.tag::after{content:")"}
.tag.proven{color:var(--green)}.tag.refuted{color:var(--red)}.tag.split{color:var(--amber)}
.trow.dec{border:1px solid var(--line2);border-radius:8px;padding:8px 10px;margin:6px 0;background:#101010}
.trow.dec .meta{margin-left:0}
.act{display:flex;gap:12px;margin:6px 0 2px;align-items:center}
.act input{flex:1}
.opt{color:var(--dim)}
.opt b{color:var(--ink);font-weight:400}
.opt:hover,.opt:hover b{color:#fff}
.opt.okb:hover{color:var(--green)}
.opt.warn:hover{color:var(--red)}
input,select,textarea{background:#161616;border:1px solid var(--line2);border-radius:6px;
padding:5px 8px;font:inherit;color:var(--ink);width:100%;margin:2px 0 7px}
input:focus,textarea:focus,select:focus{outline:none;border-color:var(--accent)}
label{font-size:11px;color:var(--dim)}
.card{border:1px solid var(--line2);border-radius:8px;padding:10px 12px;margin:8px 0;background:#101010}
.card h4{margin:0 0 4px;font-size:12.5px}
.dim{color:var(--dim);font-size:11.5px}
main{display:flex;flex-direction:column;min-width:0;background:var(--bg);grid-row:1}
.welcome{border:1px solid var(--line2);border-radius:10px;margin:12px 14px 2px;
padding:10px 14px;color:var(--dim)}
.welcome .t1{color:var(--ink);font-size:13.5px}
.welcome .spark{color:var(--accent);font-size:15px}
.welcome .row2{display:flex;gap:18px;flex-wrap:wrap;font-size:11.5px;color:var(--faint);margin-top:2px}
.modes{display:flex;gap:6px;padding:8px 14px 4px;flex-wrap:wrap;align-items:center}
.modes .lbl{color:var(--faint);font-size:11.5px}
.modes button{color:var(--faint);padding:1px 7px;border-radius:5px}
.modes button:hover{color:var(--ink)}
.modes button.on{color:var(--accent);background:#221610}
.modes .hint{margin-left:auto;color:var(--faint);font-size:11px}
#forkbar{display:none;padding:3px 14px;font-size:11.5px;color:var(--amber)}
#forkbar a{color:var(--amber)}
#msgs{flex:1;overflow-y:auto;padding:8px 14px 12px}
.ev{padding:2px 6px;border-radius:4px;cursor:pointer}
.ev:hover{background:#131313}
.ev.sel{background:#221a0d;box-shadow:inset 2px 0 0 var(--amber)}
.ev .hd{color:var(--dim)}
.ev .hd .who{color:var(--ink);font-weight:700}
.ev .hd .tm{color:var(--faint);font-size:11px}
.ev .bd{margin:1px 0 3px 15px;white-space:pre-wrap;word-break:break-word;color:var(--ink)}
.ev.user{background:var(--userbg);border-radius:6px;padding:5px 8px;margin:5px 0}
.ev.user .bd{margin-left:15px}
.ev.agent .bd{color:#c9c9c9}
.gt{color:var(--ink);font-weight:700}
.mk{font-weight:400}
.mk.green{color:var(--green)}.mk.red{color:var(--red)}.mk.amber{color:var(--amber)}
.mk.blue{color:var(--blue)}.mk.purple{color:var(--purple)}.mk.gray{color:#8a8f98}
.mk.acc{color:var(--accent)}
.res{color:var(--dim)}
.res .oc{color:var(--ink)}
.fork{color:var(--amber);font-size:11px;margin-left:15px}
.spin{color:var(--accent);padding:2px 6px}
.spin .verb{color:var(--dim);font-style:italic}
.spin .el{color:var(--faint);font-style:normal}
#composer{padding:4px 14px 10px;background:var(--bg);position:relative}
#slashmenu{display:none;border:1px solid var(--line2);border-radius:8px;background:#101010;
margin-bottom:6px;padding:4px 0}
#slashmenu .it{padding:3px 12px;cursor:pointer;color:var(--dim);display:flex;gap:12px}
#slashmenu .it:hover,#slashmenu .it.on{background:#221610;color:var(--ink)}
#slashmenu .it .c{color:var(--accent);min-width:64px}
.cbox{border:1px solid var(--line2);border-radius:10px;background:var(--bg);padding:7px 12px 5px}
.cbox:focus-within{border-color:#575757}
.crow{display:flex;gap:8px;align-items:flex-start}
.crow .gt{padding-top:2px}
.cbox textarea{border:0;background:transparent;margin:0;padding:2px 0;resize:none;width:100%;color:var(--ink)}
.cbox textarea:focus{outline:none;border:0}
.cbox textarea::placeholder{color:var(--faint)}
.cfoot{display:flex;gap:14px;align-items:center;padding-top:5px;margin-top:3px;
font-size:11px;color:var(--faint)}
.cfoot .mode{color:var(--amber)}
.cfoot .sp{margin-left:auto;display:flex;gap:12px;align-items:center}
.cfoot .send{color:var(--accent)}
.cfoot .send:hover{text-decoration:underline;color:var(--accent)}
nav{border-left:1px solid var(--line);overflow-y:auto;padding:10px 10px;grid-row:1}
nav h3{font-size:12px;font-weight:700;margin:0 0 4px;color:var(--ink)}
.node{padding:2px 6px;border-radius:4px;cursor:pointer;font-size:11px;color:var(--faint);
white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.node:hover{background:#131313;color:var(--dim)}
.node.sel{background:#221a0d;color:var(--ink)}
.node.sel::before{content:"❯ ";color:var(--amber)}
.node .a{color:var(--faint)}
footer{grid-column:1/4;border-top:1px solid var(--line);display:flex;gap:16px;
align-items:center;padding:0 12px;font-size:11px;color:var(--faint);
overflow:hidden;white-space:nowrap;background:var(--bg)}
footer .acc{color:var(--accent)}
footer .warn{color:var(--amber)}
footer .meter{display:inline-block;letter-spacing:-1px}
footer .right{margin-left:auto;display:flex;gap:16px;align-items:center}
footer .lang button{color:var(--faint);padding:0 3px;font-size:11px}
footer .lang button.on{color:var(--accent)}
.dlg{border:1px solid var(--line2);border-radius:10px;padding:10px 14px;margin:8px 0;background:#101010;cursor:default}
.dlg .q{color:var(--ink);font-weight:700}
.dlg .why{color:var(--dim);margin:3px 0}
.dlg .cons{color:var(--faint);font-size:11.5px}
.dlg .opts{display:flex;gap:22px;margin-top:7px}
.dlg .opts button{color:var(--dim)}
.dlg .opts button.cur{color:var(--ink)}
.dlg .opts button.cur::before{content:"❯ ";color:var(--accent)}
.dlg .opts button:hover{color:#fff}
.dlg input{margin-top:7px}
.ev .detail{display:none;margin:1px 0 3px 15px;color:var(--dim);font-size:12px;
border-left:1px solid #2e2e33;padding-left:11px;white-space:pre-wrap}
.ev.open .detail{display:block}
.sysline{color:var(--faint);padding:2px 6px;font-size:12px}
.sysline .spark{color:var(--accent)}
.sysline.err{color:var(--red)}
.qtag{color:var(--amber);font-size:11px}
#toast{position:fixed;bottom:36px;left:50%;transform:translateX(-50%);
background:#161616;color:var(--ink);border:1px solid var(--line2);padding:6px 13px;
border-radius:8px;font-size:12px;display:none;z-index:9}
svg text{font-size:10px;fill:var(--dim)}
@media (max-width:1080px){body{grid-template-columns:264px 1fr}nav{display:none}footer{grid-column:1/3}}
</style></head><body>
<aside>
  <h1><span class="spark">✻</span> mechanism-agent</h1>
  <div class="sub"><span data-t="subtitle"></span><span id="ver"></span></div>
  <div style="display:flex;gap:14px;margin-top:8px">
    <button class="abtn" onclick="runCycle()" data-t="wake"></button>
    <button onclick="showTaskForm('leaf')" data-t="add_leaf"></button>
    <button onclick="showTaskForm('ticket')" data-t="add_ticket"></button>
  </div>
  <div class="stabs" id="stabs"></div>
  <div id="side-tasks"></div>
  <div id="side-agents" style="display:none"></div>
  <div id="side-graph" style="display:none"></div>
  <form id="leaf-form" class="card" style="display:none" onsubmit="return postLeaf(event)">
    <h4 data-t="leaf_form_title"></h4>
    <label data-t="f_id"></label><input name="leaf_id" placeholder="L1">
    <label data-t="f_task"></label><input name="task" required data-t-ph="f_task_ph">
    <label data-t="f_checker"></label><select name="checker" id="checker-sel"></select>
    <label data-t="f_args"></label><input name="checker_args" placeholder='{"n": 200}'>
    <button type="submit" class="abtn" data-t="f_open"></button></form>
  <form id="ticket-form" class="card" style="display:none" onsubmit="return postTicket(event)">
    <h4 data-t="ticket_form_title"></h4>
    <label data-t="f_title"></label><input name="title" required>
    <label data-t="f_owner"></label><input name="owner">
    <label data-t="f_decider"></label><input name="decider">
    <label data-t="f_trigger"></label><input name="next_trigger">
    <button type="submit" class="abtn" data-t="f_create"></button></form>
  <form id="agent-form" class="card" style="display:none" onsubmit="return postAgent(event)">
    <h4 id="agent-form-title"></h4>
    <label data-t="a_name"></label><input name="name" required placeholder="worker-3">
    <label data-t="a_role"></label><select name="role">
      <option value="worker">worker</option>
      <option value="reviewer">reviewer</option>
      <option value="coordinator">coordinator</option></select>
    <label data-t="a_model"></label><input name="model" placeholder="gpt-… / deepseek-…">
    <label data-t="a_base"></label><input name="base_url" placeholder="https://…/v1">
    <label data-t="a_keyenv"></label><input name="api_key_env" placeholder="MECH_AGENT_API_KEY">
    <label>Temperature</label><input name="temperature" type="number" step="0.1" min="0" max="2" value="0">
    <label><input type="checkbox" name="enabled" checked style="width:auto"> <span data-t="a_enabled"></span></label><br>
    <button type="submit" class="abtn" data-t="a_save"></button>
    <button type="button" onclick="hideAgentForm()" data-t="a_cancel"></button></form>
</aside>
<main>
  <div class="welcome"><span class="spark">✻</span> <span class="t1">mechanism-agent</span>
    <span id="w-ver"></span>
    <div class="row2"><span data-t="welcome_1"></span><span data-t="welcome_2"></span><span data-t="welcome_3"></span></div></div>
  <div class="modes" id="channels"></div>
  <div id="forkbar"></div>
  <div id="msgs"></div>
  <div id="composer">
    <div id="slashmenu"></div>
    <div class="cbox">
      <div class="crow"><span class="gt">&gt;</span><textarea id="input" rows="2"></textarea></div>
      <div class="cfoot"><span class="mode" id="c-mode"></span>
      <span id="c-fork"></span>
      <span>? for shortcuts</span>
      <span class="sp"><span id="c-model"></span><button class="send" onclick="sendChat()" data-t="send"></button></span></div>
    </div>
  </div>
</main>
<nav>
  <h3 data-t="navi_title"></h3>
  <div class="dim" style="margin-bottom:8px" data-t="navi_help"></div>
  <div id="nodes"></div>
  <button onclick="clearFork()" style="margin-top:8px;color:var(--dim)" data-t="navi_clear"></button>
</nav>
<footer id="statusbar"></footer>
<div id="toast"></div>
<script>
const L={
en:{subtitle:"research-mechanism console",wake:"⏵ Wake one round",
add_leaf:"＋ Leaf",add_ticket:"＋ Ticket",tab_tasks:"Tasks",tab_agents:"Agents",tab_graph:"Graph",
welcome_1:"the ledger is the only truth",welcome_2:"chat persists · fork from any message",welcome_3:"writes go through Board / Tickets rules",
decisions:"⏸ Awaiting your decision",leaves:"Leaves",tickets:"Tickets",agents:"Agents",
graph:"Graph",approve:"❯ Approve",reject:"Reject",done:"Done",drop:"Drop",edit:"edit",del:"delete",
note_ph:"note (optional)",decider:"decider",trigger:"trigger",owner:"owner",no_checker:"no checker",
no_leaves:"No leaves yet.",no_tickets:"No tickets yet.",claimed:"claimed",delivered:"delivered",closed_by:"closed",
add_agent:"＋ Add member",model_global:"(global / demo)",stats:"claimed {c} · delivered {d} · closed {x}",
last:"last",disabled:"disabled",graph_note:"Lines = interactions that actually happened (dispatch / deliver / close / chat); numbers are counts. Edit a member to change its model parameters.",
channel:"channel",all:"all",chan_hint:"click any message to set a fork point",you:"You",
fork_from:"↳ forked from #",fork_bar:"↳ Fork point: message #{id} — the next message grows a new branch from here.",
cancel:"cancel",empty_chan:"Nothing here yet. Send the first message below (or /run to wake a round).",
k_open:"Opened",k_claim:"Claimed",k_deliver:"Delivered",k_close:"Closed",k_stuck:"Stuck",k_release:"Released",
sb_ctx:"leaves",sb_open:"open",sb_closed:"closed",sb_tickets:"tickets",
sb_decisions:"⏸ {n} awaiting you",sb_channel:"channel",sb_model:"model",
leaf_form_title:"Open a leaf",f_id:"ID (blank = auto)",f_task:"Task",f_task_ph:"One machine-gradable question",
f_checker:"Checker",f_args:"Args JSON",f_open:"Open",ticket_form_title:"New ticket",f_title:"Title",
f_owner:"Owner",f_decider:"Decider (user = decision queue)",f_trigger:"Next trigger",f_create:"Create",
agent_new:"Add member",agent_edit:"Edit member ",a_name:"Name",a_role:"Role",
a_model:"Model (blank = global / demo backend)",a_base:"Base URL (OpenAI-compatible endpoint)",
a_keyenv:"Env var holding the API key (name only, never the key)",a_enabled:"Enabled",a_save:"Save",a_cancel:"Cancel",
navi_title:"Prompt Navigator",navi_help:"Click a node to jump to that message and set it as the fork point. The next message grows a new branch there; the original line is kept.",
navi_clear:"⏎ back to latest (clear fork)",composer_ph:"Message a member, or type / for commands…",
send:"Send ⏎",
t_waking:"Waking…",t_round:"Round: proven {p} · refuted {r} · split {s}",t_error:"Error: ",
t_leaf:"Leaf opened: ",t_ticket:"Ticket created #",t_decided:"Decision recorded",t_deleted:"Deleted ",
t_saved:"Member saved: ",t_help:"/run wake a round · /leaf <task> open a leaf · /ticket <title> new ticket · click a message to fork",
confirm_del:"Delete member {name}? (history is kept)",fork_chip:"↳ fork from #",
verbs:["Pondering","Cogitating","Synthesizing","Deliberating","Mulling","Reasoning","Thinking"],
cmd_run:"wake one round",cmd_leaf:"open a leaf",cmd_ticket:"new ticket",cmd_help:"show help",
dlg_q:"Ticket #{id} awaits your decision",dlg_cons:"Approve closes it as done · Reject closes it as dropped · keys 1 / 2 answer the top dialog",
mode_manual:"⏵⏵ wake: manual",backend_demo:"demo backend",queued:"queued → next round",
sys_round:"Round complete",sys_err:"Error",expand_hint:"click a tool line to expand · ctrl+o toggles all"},
ja:{subtitle:"研究メカニズム・コンソール",wake:"⏵ 一ラウンド起こす",
add_leaf:"＋ リーフ",add_ticket:"＋ チケット",tab_tasks:"タスク",tab_agents:"メンバー",tab_graph:"関係図",
welcome_1:"台帳が唯一の真実",welcome_2:"会話は永続保存 · 任意のメッセージから分岐",welcome_3:"書き込みは Board / Tickets の規則を通る",
decisions:"⏸ あなたの決定待ち",leaves:"リーフ",tickets:"チケット",agents:"メンバー",
graph:"関係図",approve:"❯ 承認",reject:"却下",done:"完了",drop:"破棄",edit:"編集",del:"削除",
note_ph:"メモ（任意）",decider:"決定者",trigger:"トリガー",owner:"担当",no_checker:"チェッカーなし",
no_leaves:"リーフはまだない。",no_tickets:"チケットはまだない。",claimed:"請求",delivered:"納品",closed_by:"クローズ",
add_agent:"＋ メンバー追加",model_global:"（全体／デモ）",stats:"請求 {c} · 納品 {d} · クローズ {x}",
last:"最近",disabled:"無効",graph_note:"線＝実際に起きたやり取り（派遣／納品／クローズ／対話）、数字は回数。メンバーの編集でモデルパラメータを変更できる。",
channel:"チャンネル",all:"全体",chan_hint:"メッセージをクリックで分岐点に",you:"あなた",
fork_from:"↳ 分岐元 #",fork_bar:"↳ 分岐点：メッセージ #{id} — 次のメッセージはここから新しい枝を伸ばす。",
cancel:"取消",empty_chan:"まだ何もない。下から最初のメッセージを送る（または /run で一ラウンド）。",
k_open:"開題",k_claim:"請求",k_deliver:"納品",k_close:"クローズ",k_stuck:"停滞",k_release:"解放",
sb_ctx:"リーフ",sb_open:"開",sb_closed:"閉",sb_tickets:"チケット",
sb_decisions:"⏸ 要決定 {n} 件",sb_channel:"チャンネル",sb_model:"モデル",
leaf_form_title:"リーフを開く",f_id:"ID（空欄＝自動）",f_task:"課題",f_task_ph:"機械で判定できる一問",
f_checker:"チェッカー",f_args:"引数 JSON",f_open:"開く",ticket_form_title:"新規チケット",f_title:"タイトル",
f_owner:"担当者",f_decider:"決定者（user＝要決定キュー）",f_trigger:"次のトリガー",f_create:"作成",
agent_new:"メンバー追加",agent_edit:"メンバー編集 ",a_name:"名前",a_role:"役割",
a_model:"モデル（空欄＝全体／デモバックエンド）",a_base:"Base URL（OpenAI 互換エンドポイント）",
a_keyenv:"API キーを保持する環境変数名（名前のみ、キー自体は保存しない）",a_enabled:"有効",a_save:"保存",a_cancel:"キャンセル",
navi_title:"Prompt ナビ",navi_help:"ノードをクリック：そのメッセージへ移動し分岐点に設定。次のメッセージはそこから新しい枝を伸ばす（元の線は保持）。",
navi_clear:"⏎ 最新へ戻る（分岐を解除）",composer_ph:"メンバーへメッセージ、または / でコマンド…",
send:"送信 ⏎",
t_waking:"起動中…",t_round:"本ラウンド：証明 {p} · 反証 {r} · 分割 {s}",t_error:"エラー：",
t_leaf:"リーフを開いた：",t_ticket:"チケット作成 #",t_decided:"決定を記録した",t_deleted:"削除した ",
t_saved:"メンバーを保存：",t_help:"/run 一ラウンド · /leaf 課題 リーフを開く · /ticket 題名 チケット作成 · メッセージのクリックで分岐",
confirm_del:"メンバー {name} を削除する？（履歴は残る）",fork_chip:"↳ 分岐元 #",
verbs:["思考中","推論中","検討中","熟考中","統合中"],
cmd_run:"一ラウンド起こす",cmd_leaf:"リーフを開く",cmd_ticket:"チケット作成",cmd_help:"ヘルプ表示",
dlg_q:"チケット #{id} があなたの決定待ち",dlg_cons:"承認＝完了で閉じる · 却下＝破棄で閉じる · キー 1 / 2 で先頭のダイアログに回答",
mode_manual:"⏵⏵ 起動：手動",backend_demo:"デモバックエンド",queued:"キュー済 → 次ラウンド",
sys_round:"ラウンド完了",sys_err:"エラー",expand_hint:"ツール行クリックで展開 · ctrl+o で全展開切替"}};
let lang=localStorage.getItem("mech-lang")||"en"; if(!L[lang])lang="en";
const t=(k,v)=>{let s=L[lang][k]||L.en[k]||k;if(v)for(const x in v)s=String(s).replace("{"+x+"}",v[x]);return s};
let S=null, channel="all", sideTab="tasks", forkParent=null, lastNearBottom=true, spinTimer=null;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tm=ts=>new Date(ts*1000).toLocaleTimeString();
function toast(x){const e=$("toast");e.textContent=x;e.style.display="block";
  setTimeout(()=>e.style.display="none",3600)}
async function api(path,body){const r=await fetch(path,{method:body?"POST":"GET",
  headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);return d}
function thread(){return S.chat.filter(m=>m.channel===channel||m.channel==="all")}
function curAgent(){return S.agents.find(a=>a.name===channel)}
function applyStatic(){document.querySelectorAll("[data-t]").forEach(e=>e.textContent=t(e.dataset.t));
  document.querySelectorAll("[data-t-ph]").forEach(e=>e.placeholder=t(e.dataset.tPh));
  $("input").placeholder=t("composer_ph");document.documentElement.lang=lang==="ja"?"ja":"en"}
function meter(pct){const n=10,f=Math.round(pct/100*n);return "█".repeat(f)+"░".repeat(n-f)}
function render(){
  if(!S)return;
  applyStatic();
  $("ver").textContent=S.version?" · v"+S.version:"";
  $("w-ver").textContent=S.version?" · v"+S.version:"";
  $("stabs").innerHTML=[["tasks",t("tab_tasks")],["agents",t("tab_agents")],["graph",t("tab_graph")]].map(([k,v])=>
    `<button class="${sideTab===k?"on":""}" onclick="sideTab='${k}';render()">${v}${k==="tasks"&&S.counts.decisions?`<span class="badge">(${S.counts.decisions})</span>`:""}</button>`).join("");
  for(const k of["tasks","agents","graph"]) $("side-"+k).style.display=sideTab===k?"block":"none";
  const tot=S.counts.leaves_open+S.counts.leaves_closed;
  const pct=tot?Math.round(100*S.counts.leaves_closed/tot):0;
  const a=curAgent();
  $("statusbar").innerHTML=
    `<span><span class="acc">✻</span> mechanism-agent${S.version?" v"+S.version:""}</span>`+
    `<span>${t("sb_ctx")} <span class="meter">${meter(pct)}</span> ${pct}% (${S.counts.leaves_closed}/${tot})</span>`+
    `<span>${t("sb_tickets")} ${S.counts.tickets_open} ${t("sb_open")}</span>`+
    (S.counts.decisions?`<span class="warn">${t("sb_decisions",{n:S.counts.decisions})}</span>`:"")+
    `<span class="right"><span class="lang"><button class="${lang==="en"?"on":""}" onclick="setLang('en')">EN</button>|<button class="${lang==="ja"?"on":""}" onclick="setLang('ja')">日本語</button></span>`+
    `<span>${t("sb_channel")} ${channel==="all"?t("all"):esc(channel)}</span>`+
    `<span>${t("sb_model")} ${esc(a?(a.model||t("model_global")):"—")}</span></span>`;
  $("c-mode").textContent=t("mode_manual")+" · "+(a?(a.model||t("backend_demo")):t("backend_demo"));
  $("c-model").textContent=a?((a.model||t("model_global"))):"";
  $("c-fork").textContent=forkParent?(t("fork_chip")+forkParent):"";
  renderTasks();renderAgents();renderGraph();renderChat();
}
function setLang(x){lang=x;localStorage.setItem("mech-lang",x);render()}
function renderTasks(){
  const el=$("side-tasks");if(document.activeElement&&el.contains(document.activeElement)&&
    /INPUT|TEXTAREA/.test(document.activeElement.tagName))return;
  let h="";
  if(S.decisions.length){h+=`<div class="sect">${t("decisions")}</div>`+S.decisions.map(x=>`
    <div class="trow dec"><div class="r1"><span class="ttl">#${x.id} ${esc(x.title)}</span></div>
    <div class="meta">${t("decider")} ${esc(x.decider)} · ${t("trigger")} ${esc(x.next_trigger||"—")}</div>
    <div class="act"><input id="note-${x.id}" placeholder="${t("note_ph")}">
    <button class="opt okb" onclick="decide(${x.id},'approve')">${t("approve")}</button>
    <button class="opt warn" onclick="decide(${x.id},'reject')">${t("reject")}</button></div></div>`).join("")}
  h+=`<div class="sect">${t("leaves")}</div>`+(S.leaves.map(l=>`
    <div class="trow"><div class="r1"><span class="sdot ${l.status==="closed"?l.outcome:l.status}">●</span>
    <span class="id">${esc(l.leaf_id)}</span><span class="ttl">${esc(l.task)}</span>
    <span class="tag ${l.status==="closed"?l.outcome:""}">${l.status==="closed"?l.outcome:l.status}</span></div>
    <div class="meta">${esc(l.checker||t("no_checker"))}${l.claimed_by?" · "+esc(l.claimed_by):""}${l.delivered_by?" → "+esc(l.delivered_by):""}${l.closed_by?" · "+esc(l.closed_by):""}</div></div>`).join("")||`<div class="dim">${t("no_leaves")}</div>`);
  h+=`<div class="sect">${t("tickets")}</div>`+(S.tickets.map(x=>`
    <div class="trow"><div class="r1"><span class="sdot ${x.status==="closed"?"closed":"open"}">●</span>
    <span class="id">#${x.id}</span><span class="ttl">${esc(x.title)}</span>
    <span class="tag">${x.status}</span></div>
    <div class="meta">${t("owner")} ${esc(x.owner||"—")} · ${t("decider")} ${esc(x.decider||"—")}</div>
    ${x.status!=="closed"?`<div class="act" style="margin-left:15px"><button class="opt okb" onclick="closeTicket(${x.id},'done')">${t("done")}</button>
    <button class="opt warn" onclick="closeTicket(${x.id},'dropped')">${t("drop")}</button></div>`:""}</div>`).join("")||`<div class="dim">${t("no_tickets")}</div>`);
  el.innerHTML=h;
}
function renderAgents(){
  const el=$("side-agents");
  el.innerHTML=`<div class="sect">${t("agents")}</div>`+S.agents.map(a=>`
   <div class="trow"><div class="r1"><span class="sdot" style="color:${!a.enabled?"#555":a.state==="Active"?"var(--green)":"#8a8f98"}">●</span>
    <span class="ttl" style="flex:none">${esc(a.name)}</span><span class="tag">${a.role}</span>
    <span class="tag">${a.enabled?a.state:t("disabled")}</span>
    <span style="margin-left:auto;display:flex;gap:10px"><button class="opt" onclick='editAgent(${JSON.stringify(a.name)})'>${t("edit")}</button>
    <button class="opt warn" onclick='delAgent(${JSON.stringify(a.name)})'>${t("del")}</button></span></div>
    <div class="meta">${esc(a.model||t("model_global"))}${a.base_url?" · "+esc(a.base_url):""} · temp ${a.temperature}</div>
    <div class="meta">${t("stats",{c:a.stats.claimed,d:a.stats.delivered,x:a.stats.closed})}${a.last?" · "+t("last")+" "+esc(a.last):""}</div></div>`).join("")
   +`<button class="abtn" onclick="newAgent()" style="margin-top:8px">${t("add_agent")}</button>`;
}
function renderGraph(){
  const el=$("side-graph");const g=S.graph;
  const cx=140,cy=118,R=84;const pos={user:[cx,cy]};
  const others=g.nodes.filter(n=>n.name!=="user");
  others.forEach((n,i)=>{const ang=2*Math.PI*i/Math.max(others.length,1)-Math.PI/2;
    pos[n.name]=[cx+R*Math.cos(ang),cy+R*Math.sin(ang)]});
  const col={dispatch:"#636363",deliver:"#58a6ff",close:"#4caf7d",chat:"#b083f0",reply:"#2a9f8f"};
  let s=`<div class="sect">${t("graph")}</div><svg width="272" height="236" viewBox="0 0 280 236">`;
  for(const e of g.edges){const a=pos[e.from],b=pos[e.to];if(!a||!b)continue;
    s+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${col[e.kind]||"#444"}" stroke-width="1.2"/>
    <text x="${(a[0]+b[0])/2}" y="${(a[1]+b[1])/2-3}">${e.kind} ×${e.count}</text>`}
  for(const n of g.nodes){const p=pos[n.name];
    s+=`<circle cx="${p[0]}" cy="${p[1]}" r="14" fill="${n.name==="user"?"#d97757":"#101010"}" stroke="#d97757"/>
    <text x="${p[0]}" y="${p[1]+25}" text-anchor="middle">${esc(n.name)}</text>
    <text x="${p[0]}" y="${p[1]+3}" text-anchor="middle" fill="${n.name==="user"?"#14100d":"#d97757"}">${n.name==="user"?"U":esc(n.role[0].toUpperCase())}</text>`}
  el.innerHTML=s+"</svg>"+`<div class="dim">${t("graph_note")}</div>`;
}
const KINDMK={open:["●","gray","k_open"],claim:["●","blue","k_claim"],deliver:["●","purple","k_deliver"],
  close:["●","green","k_close"],stuck:["●","amber","k_stuck"],release:["●","gray","k_release"]};
let sysLines=[], expandAll=false, running=false;
function transcriptItems(){
  const items=thread().map(m=>({ts:m.ts,type:"chat",m}));
  if(channel==="all"){
    for(const e of S.feed)items.push({ts:e.ts,type:"tool",e});
    for(const d of S.decisions)items.push({ts:0,type:"dlg",d});
    for(const x of sysLines)items.push({ts:x.ts,type:"sys",x});
  }
  return items.sort((x,y)=>x.ts-y.ts);
}
function sys(text,err){sysLines.push({ts:Date.now()/1000,text,err:!!err});if(sysLines.length>30)sysLines.shift()}
function renderChat(){
  const chans=["all",...S.agents.filter(a=>a.role!=="coordinator").map(a=>a.name)];
  if(!chans.includes(channel))channel="all";
  $("channels").innerHTML=`<span class="lbl">${t("channel")}</span>`+chans.map(c=>
    `<button class="${c===channel?"on":""}" onclick="channel='${c}';forkParent=null;render()">${c==="all"?t("all"):c}</button>`).join("")
    +`<span class="hint">${t("chan_hint")} · ${t("expand_hint")}</span>`;
  const items=transcriptItems();const box=$("msgs");
  const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<80;
  let prev=null;
  box.innerHTML=items.map(it=>{
    if(it.type==="sys"){const x=it.x;
      return `<div class="sysline ${x.err?"err":""}"><span class="spark">${x.err?"✻":"✻"}</span> ${esc(x.text)}</div>`}
    if(it.type==="dlg"){const d=it.d;
      return `<div class="dlg"><div class="q">⏸ ${t("dlg_q",{id:d.id})}</div>
      <div class="why">${esc(d.title)}</div>
      <div class="cons">${t("decider")} ${esc(d.decider)} · ${t("trigger")} ${esc(d.next_trigger||"—")} · ${t("dlg_cons")}</div>
      <input id="dnote-${d.id}" placeholder="${t("note_ph")}">
      <div class="opts"><button class="cur" onclick="decide(${d.id},'approve')">1. ${t("approve").replace("❯ ","")}</button>
      <button onclick="decide(${d.id},'reject')">2. ${t("reject")}</button></div></div>`}
    if(it.type==="tool"){const e=it.e;const k=KINDMK[e.kind]||["●","gray",null];
      const lf=S.leaves.find(l=>l.leaf_id===e.leaf);
      const det=lf?`${esc(lf.task)}\n${t("f_checker")}: ${esc(lf.checker||"—")} ${lf.checker_args?esc(JSON.stringify(lf.checker_args)):""}\n${t("claimed")}: ${esc(lf.claimed_by||"—")} · ${t("delivered")}: ${esc(lf.delivered_by||"—")} · ${t("closed_by")}: ${esc(lf.closed_by||"—")}`:"";
      return `<div class="ev ${expandAll?"open":""}" onclick="this.classList.toggle('open')"><span class="mk ${k[1]}">${k[0]}</span>
      <span class="who" style="font-weight:700">${k[2]?t(k[2]):e.kind} ${esc(e.leaf||"")}</span>
      <span class="tm" style="color:var(--faint);font-size:11px"> ${tm(e.ts)}</span>
      <div class="bd res">⎿ ${e.by?"by "+esc(e.by):""}${e.outcome?' → <span class="oc">'+esc(e.outcome)+"</span>":""}</div>${det?`<div class="detail">${det}</div>`:""}</div>`}
    const m=it.m;const forked=m.parent_id&&prev!==null&&m.parent_id!==prev;prev=m.id;
    if(m.author==="user")return `<div class="ev user ${forkParent===m.id?"sel":""}" id="msg-${m.id}" onclick="setFork(${m.id})">
      <span class="gt">&gt;</span> <span class="who" style="font-weight:700">${t("you")}</span> <span class="tm" style="color:var(--faint);font-size:11px">#${m.id} · ${tm(m.ts)}${m.channel!=="all"&&channel==="all"?" · @"+esc(m.channel):""}</span>
      ${forked?`<div class="fork">${t("fork_from")}${m.parent_id}</div>`:""}
      <div class="bd">${esc(m.text)}</div></div>`;
    const mk=m.kind==="summary"?["✻","acc"]:["●","blue"];
    return `<div class="ev agent ${forkParent===m.id?"sel":""}" id="msg-${m.id}" onclick="setFork(${m.id})">
      <span class="mk ${mk[1]}">${mk[0]}</span> <span class="who" style="font-weight:700">${esc(m.author)}</span> <span class="tm" style="color:var(--faint);font-size:11px">#${m.id} · ${tm(m.ts)}</span>
      ${forked?`<div class="fork">${t("fork_from")}${m.parent_id}</div>`:""}
      <div class="bd">${esc(m.text)}</div></div>`}).join("")||`<div class="dim">${t("empty_chan")}</div>`;
  if(nearBottom||lastNearBottom)box.scrollTop=box.scrollHeight;
  lastNearBottom=nearBottom;
  const fb=$("forkbar");
  if(forkParent){fb.style.display="block";
    fb.innerHTML=t("fork_bar",{id:forkParent})+` <a href="#" onclick="clearFork();return false">${t("cancel")}</a>`}
  else fb.style.display="none";
  $("nodes").innerHTML=thread().slice().reverse().map(m=>
    `<div class="node ${forkParent===m.id?"sel":""}" onclick="jumpTo(${m.id})">
    <span class="a">#${m.id} ${esc(m.author)}</span> ${esc(m.text.slice(0,30))}</div>`).join("");
  const sel=$("checker-sel");
  if(sel&&sel.options.length===0)sel.innerHTML=`<option value="">(${t("no_checker")})</option>`+S.checkers.map(c=>`<option>${c}</option>`).join("");
}
function setFork(id){forkParent=id;render();
  const e=$("msg-"+id);if(e)e.scrollIntoView({block:"center"})}
function jumpTo(id){setFork(id)}
function clearFork(){forkParent=null;render();const b=$("msgs");b.scrollTop=b.scrollHeight}
const CMDS=[["/run","cmd_run"],["/leaf ","cmd_leaf"],["/ticket ","cmd_ticket"],["/help","cmd_help"]];
function slashMenu(){
  const v=$("input").value;const m=$("slashmenu");
  if(!v.startsWith("/")||v.includes(" ",1)&&v.length>8){m.style.display="none";return}
  const items=CMDS.filter(([c])=>c.startsWith(v.split(" ")[0])||v==="/");
  if(!items.length||v==="/run"&&false){m.style.display="none";return}
  m.innerHTML=items.map(([c,d])=>`<div class="it" onclick="pickCmd('${c}')"><span class="c">${c.trim()}</span><span>${t(d)}</span></div>`).join("");
  m.style.display=items.length?"block":"none";
}
function pickCmd(c){const ta=$("input");
  if(c==="/run"){ta.value="";$("slashmenu").style.display="none";runCycle();return}
  if(c==="/help"){ta.value="";$("slashmenu").style.display="none";toast(t("t_help"));return}
  ta.value=c;ta.focus();$("slashmenu").style.display="none"}
$("input").addEventListener("input",slashMenu);
let hist=[], histIdx=-1;
async function sendChat(){const ta=$("input");const text=ta.value.trim();if(!text)return;
  hist.push(text);histIdx=hist.length;
  $("slashmenu").style.display="none";
  const wasRunning=running;
  try{
    if(text==="/help"){toast(t("t_help"));ta.value="";return}
    if(text==="/run"){ta.value="";runCycle();return}
    if(text.startsWith("/leaf ")){await api("/api/leaf",{task:text.slice(6)});ta.value="";toast(t("t_leaf"));refresh();return}
    if(text.startsWith("/ticket ")){await api("/api/ticket",{title:text.slice(8)});ta.value="";toast(t("t_ticket"));refresh();return}
    await api("/api/chat",{channel,text,parent_id:forkParent});ta.value="";forkParent=null;
    if(wasRunning)sys(t("queued")+": "+text.slice(0,60));refresh()}
  catch(e){toast(t("t_error")+e.message)}}
$("input").addEventListener("keydown",e=>{
  if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat()}
  if(e.key==="Escape"){$("slashmenu").style.display="none"}
  if(e.key==="ArrowUp"&&histIdx>0){e.preventDefault();histIdx--;$("input").value=hist[histIdx]||""}
  if(e.key==="ArrowDown"&&histIdx<hist.length){e.preventDefault();histIdx++;$("input").value=hist[histIdx]||""}
  if(e.key==="Tab"&&e.shiftKey){e.preventDefault();
    const chans=["all",...S.agents.filter(a=>a.role!=="coordinator").map(a=>a.name)];
    const i=chans.indexOf(channel);channel=chans[(i+1)%chans.length];forkParent=null;render()}});
document.addEventListener("keydown",e=>{
  if(e.ctrlKey&&e.key==="o"){e.preventDefault();expandAll=!expandAll;render()}
  if((e.key==="1"||e.key==="2")&&S&&S.decisions.length&&!/INPUT|TEXTAREA/.test(document.activeElement.tagName)){
    decide(S.decisions[0].id, e.key==="1"?"approve":"reject")}});
function startSpin(){
  stopSpin();
  const box=$("msgs");const d=document.createElement("div");d.className="spin";d.id="spinner";
  const verbs=L[lang].verbs||L.en.verbs;const verb=verbs[Math.floor(Math.random()*verbs.length)];
  const frames=["✢","✳","✶","✻","✽"];let i=0;const t0=Date.now();
  d.innerHTML=`<span class="g">${frames[0]}</span> <span class="verb">${verb}…</span> <span class="el">(0s)</span>`;
  box.appendChild(d);box.scrollTop=box.scrollHeight;
  spinTimer=setInterval(()=>{i++;const s=Math.floor((Date.now()-t0)/1000);
    d.querySelector(".g").textContent=frames[i%frames.length];
    d.querySelector(".el").textContent="("+s+"s · esc to interrupt)";},120);
}
function stopSpin(){if(spinTimer)clearInterval(spinTimer);spinTimer=null;
  const d=$("spinner");if(d)d.remove()}
async function runCycle(){if(running)return;running=true;startSpin();try{const r=await api("/api/run",{});
  stopSpin();running=false;sys(t("sys_round")+": proven "+r.proven+" · refuted "+r.refuted+" · split "+r.split);refresh()}
  catch(e){stopSpin();running=false;sys(t("sys_err")+": "+e.message,true);refresh()}}
async function decide(id,decision){const n=$("dnote-"+id)||$("note-"+id);
  try{await api("/api/decide",{ticket_id:id,decision,note:n?n.value:""});sys(t("t_decided")+" #"+id+" → "+decision);refresh()}catch(e){sys(t("sys_err")+": "+e.message,true);refresh()}}
async function closeTicket(id,reason){try{await api("/api/close-ticket",{ticket_id:id,reason});refresh()}catch(e){toast(t("t_error")+e.message)}}
function showTaskForm(k){$("leaf-form").style.display=k==="leaf"?"block":"none";
  $("ticket-form").style.display=k==="ticket"?"block":"none";sideTab="tasks";render();
  $(k+"-form").scrollIntoView()}
async function postLeaf(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/leaf",Object.fromEntries(f));toast(t("t_leaf")+r.leaf_id);
  ev.target.reset();$("leaf-form").style.display="none";refresh()}catch(e){toast(t("t_error")+e.message)}return false}
async function postTicket(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/ticket",Object.fromEntries(f));toast(t("t_ticket")+r.ticket_id);
  ev.target.reset();$("ticket-form").style.display="none";refresh()}catch(e){toast(t("t_error")+e.message)}return false}
function newAgent(){$("agent-form").style.display="block";$("agent-form-title").textContent=t("agent_new");
  $("agent-form").reset();sideTab="agents";render();$("agent-form").scrollIntoView()}
function editAgent(name){const a=S.agents.find(x=>x.name===name);if(!a)return;
  const f=$("agent-form");f.style.display="block";$("agent-form-title").textContent=t("agent_edit")+name;
  const E=f.elements;E["name"].value=a.name;E["role"].value=a.role;E["model"].value=a.model;
  E["base_url"].value=a.base_url;E["api_key_env"].value=a.api_key_env;
  E["temperature"].value=a.temperature;E["enabled"].checked=a.enabled;
  sideTab="agents";render();f.scrollIntoView()}
async function delAgent(name){if(!confirm(t("confirm_del",{name})))return;
  try{await api("/api/agents/delete",{name});toast(t("t_deleted")+name);refresh()}catch(e){toast(t("t_error")+e.message)}}
async function postAgent(ev){ev.preventDefault();const f=new FormData(ev.target);
  const rec=Object.fromEntries(f);rec.enabled=f.get("enabled")==="on";rec.temperature=parseFloat(rec.temperature||"0");
  try{await api("/api/agents",rec);toast(t("t_saved")+rec.name);hideAgentForm();refresh()}catch(e){toast(t("t_error")+e.message)}return false}
function hideAgentForm(){$("agent-form").style.display="none"}
async function refresh(){try{S=await api("/api/state");render()}catch(e){}}
refresh();setInterval(refresh,3000);
$("input").focus();
</script></body></html>"""


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code: int, body: bytes, ctype: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code: int, obj) -> None:
            self._send(code, json.dumps(obj, ensure_ascii=False).encode(),
                       "application/json; charset=utf-8")

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, PAGE.encode(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                self._json(200, app.state())
            else:
                self._json(404, {"error": "not found"})

        def do_POST(self):
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length) or b"{}")
                routes = {"/api/leaf": app.open_leaf,
                          "/api/ticket": app.open_ticket,
                          "/api/decide": app.decide,
                          "/api/close-ticket": app.close_ticket,
                          "/api/message": app.message,
                          "/api/agents": app.upsert_agent,
                          "/api/agents/delete": app.delete_agent,
                          "/api/chat": app.post_chat}
                if self.path == "/api/run":
                    self._json(200, app.run_cycle())
                elif self.path in routes:
                    self._json(200, routes[self.path](data))
                else:
                    self._json(404, {"error": "not found"})
            except Exception as exc:
                self._json(400, {"error": str(exc)})

    return Handler


class _Server(ThreadingHTTPServer):
    # Never silently share the port: with address reuse on, a second
    # instance binds successfully on Windows and the browser keeps
    # hitting whichever process — the classic "deployed but nothing
    # changed". Fail loudly instead.
    allow_reuse_address = False
    daemon_threads = True


def serve(home: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = App(home)
    _Server((host, port), make_handler(app)).serve_forever()
