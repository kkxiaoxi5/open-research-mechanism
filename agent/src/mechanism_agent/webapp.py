"""Interactive web console for mechanism-agent.

The user's operating surface (PLAN decision: the UI is a required,
interactive part of the system). Styled after terminal agent tools
(Claude Code / Kilo Code): a dark transcript instead of chat bubbles —
user lines start with ``>``, agent blocks with a status dot and a
``⎿`` result connector, and board events (open/claim/deliver/close)
render as tool-call blocks interleaved in the main channel. Around
the transcript: a task sidebar (decision queue / claim board /
tickets / agent management / relation graph), a prompt navigator
that selects any message as a fork point, a composer with slash
commands (/run, /leaf, /ticket), and a status bar (leaf progress,
open tickets, current channel's model).

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
            "叫醒一轮完成：" + ("、".join(
                f"{k} ×{len(v)}" for k, v in sorted(did.items()))
                if did else "本轮无新交付") + "。",
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
                reply = ("（演示后端）收到。本轮我的工作：" +
                         ("；".join(mine) if mine else "暂无新交付") +
                         "。接真模型后我会直接答复内容。")
            self.chat.post(a["name"], a["name"], reply,
                           parent_id=pending[-1]["id"], kind="reply")

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mechanism-agent 控制台</title>
<style>
:root{--bg:#0e0e10;--panel:#16171a;--panel2:#1c1d21;--line:#2a2b31;
--ink:#e6e6e3;--dim:#8a8f98;--faint:#5c6068;--accent:#d97757;
--green:#4caf7d;--red:#e5534b;--amber:#d29922;--blue:#58a6ff;--purple:#b083f0;
--mono:ui-monospace,"Cascadia Code","SF Mono",Consolas,"Microsoft YaHei",monospace}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);display:grid;
grid-template-columns:308px 1fr 224px;grid-template-rows:1fr 26px;height:100vh;
font:13.5px/1.6 var(--mono)}
aside{background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;
padding:12px 12px 18px;grid-row:1}
aside h1{font-size:14px;margin:0;font-weight:600;letter-spacing:.2px}
aside h1 .dot{color:var(--green)}
.sub{color:var(--faint);font-size:11px;margin-top:2px}
button{background:var(--accent);color:#14100d;border:0;border-radius:6px;
padding:5px 11px;cursor:pointer;font:inherit;font-size:12.5px;font-weight:600}
button.ghost{background:var(--panel2);color:var(--ink);border:1px solid var(--line);font-weight:400}
button.small{padding:1px 8px;font-size:11.5px}
button.warn{background:transparent;color:var(--red);border:1px solid #4a2b29;font-weight:400}
button.okb{background:transparent;color:var(--green);border:1px solid #274a38;font-weight:400}
button:hover{filter:brightness(1.15)}
.sect{font-size:10.5px;letter-spacing:1.2px;color:var(--faint);text-transform:uppercase;
margin:16px 0 6px;display:flex;align-items:center;gap:6px}
.stabs{display:flex;gap:2px;margin:12px 0 2px;border-bottom:1px solid var(--line)}
.stabs button{background:none;color:var(--dim);border:0;border-bottom:2px solid transparent;
border-radius:0;padding:4px 9px;font-weight:400}
.stabs button.on{color:var(--ink);border-bottom-color:var(--accent)}
.badge{background:var(--amber);color:#14100d;border-radius:8px;padding:0 6px;
font-size:10.5px;margin-left:4px;font-weight:700}
.trow{padding:6px 8px;border-radius:6px;border:1px solid transparent;cursor:default}
.trow:hover{background:var(--panel2)}
.trow.dec{background:#241d10;border-color:#4a3a14}
.trow .r1{display:flex;gap:7px;align-items:baseline}
.trow .id{color:var(--dim);font-size:11.5px}
.trow .ttl{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.trow .meta{color:var(--faint);font-size:11px;margin-left:19px;white-space:nowrap;
overflow:hidden;text-overflow:ellipsis}
.sdot{width:7px;height:7px;border-radius:50%;flex:none;position:relative;top:-1px}
.proven{background:var(--green)}.refuted{background:var(--red)}
.split{background:var(--amber)}.open{background:#6e7681}
.claimed{background:var(--blue)}.delivered{background:var(--purple)}
.closed{background:#484f58}
.tag{font-size:10.5px;padding:0 6px;border-radius:8px;border:1px solid var(--line);color:var(--dim)}
.tag.proven{color:var(--green);border-color:#274a38}.tag.refuted{color:var(--red);border-color:#4a2b29}
.tag.split{color:var(--amber);border-color:#4a3a14}
.act{display:flex;gap:5px;margin:5px 0 2px 19px}
.act input{flex:1}
input,select,textarea{background:var(--panel2);border:1px solid var(--line);border-radius:6px;
padding:5px 8px;font:inherit;color:var(--ink);width:100%;margin:2px 0 7px}
input:focus,textarea:focus,select:focus{outline:1px solid var(--accent);border-color:var(--accent)}
label{font-size:11px;color:var(--dim)}
.card{border:1px solid var(--line);border-radius:8px;padding:10px 12px;margin:0 0 8px;background:var(--panel2)}
.card h4{margin:0 0 4px;font-size:12.5px}
.dim{color:var(--dim);font-size:11.5px}
main{display:flex;flex-direction:column;min-width:0;background:var(--bg);grid-row:1}
.modes{display:flex;gap:4px;padding:8px 12px;border-bottom:1px solid var(--line);
background:var(--panel);flex-wrap:wrap;align-items:center}
.modes .lbl{color:var(--faint);font-size:11px;margin-right:2px}
.modes button{background:transparent;color:var(--dim);border:1px solid var(--line);font-weight:400}
.modes button.on{color:var(--accent);border-color:var(--accent);background:#2a1c14}
.modes .hint{margin-left:auto;color:var(--faint);font-size:11px}
#forkbar{display:none;background:#241d10;border-bottom:1px solid #4a3a14;
padding:5px 14px;font-size:11.5px;color:var(--amber)}
#forkbar a{color:var(--amber)}
#msgs{flex:1;overflow-y:auto;padding:10px 18px 14px}
.ev{padding:5px 8px;border-radius:6px;cursor:pointer;border-left:2px solid transparent}
.ev:hover{background:#141416}
.ev.sel{background:#241d10;border-left-color:var(--amber)}
.ev .hd{font-size:12px;color:var(--dim)}
.ev .hd .who{color:var(--ink)}
.ev .hd .tm{color:var(--faint);font-size:11px}
.ev .bd{margin:2px 0 2px 7px;padding-left:11px;border-left:1px solid #2e2e33;
white-space:pre-wrap;word-break:break-word}
.ev.user{background:#1d1d20;border-radius:6px}
.ev.user .bd{border-left-color:transparent;margin-left:0;padding-left:0}
.gt{color:var(--accent);font-weight:700}
.mk{font-weight:700}
.mk.green{color:var(--green)}.mk.red{color:var(--red)}.mk.amber{color:var(--amber)}
.mk.blue{color:var(--blue)}.mk.purple{color:var(--purple)}.mk.gray{color:#6e7681}
.mk.acc{color:var(--accent)}
.res{color:var(--dim);font-size:12.5px}
.res .oc{font-weight:600}
.fork{color:var(--amber);font-size:11px}
#composer{padding:10px 14px 12px;background:var(--bg)}
.cbox{border:1px solid #3a3b42;border-radius:10px;background:var(--panel);
padding:8px 12px 6px}
.cbox:focus-within{border-color:var(--accent)}
.cbox textarea{border:0;background:transparent;margin:0;padding:2px 0;resize:none;width:100%}
.cbox textarea:focus{outline:none}
.cfoot{display:flex;gap:10px;align-items:center;border-top:1px solid var(--line);
padding-top:6px;margin-top:4px;font-size:11px;color:var(--faint)}
.cfoot .pill{color:var(--accent);border:1px solid #4a3226;border-radius:8px;padding:0 7px}
.cfoot .sp{margin-left:auto;display:flex;gap:8px;align-items:center}
.cfoot button{padding:3px 12px}
nav{background:var(--panel);border-left:1px solid var(--line);overflow-y:auto;
padding:12px 9px;grid-row:1}
nav h3{font-size:10.5px;letter-spacing:1.2px;color:var(--faint);text-transform:uppercase;margin:0 0 6px}
.node{padding:4px 7px;border-radius:5px;cursor:pointer;font-size:11px;color:var(--dim);
border-left:2px solid transparent;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.node:hover{background:var(--panel2);color:var(--ink)}
.node.sel{border-left-color:var(--amber);background:#241d10;color:var(--ink)}
.node .a{color:var(--faint)}
footer{grid-column:1/4;background:var(--panel);border-top:1px solid var(--line);
display:flex;gap:16px;align-items:center;padding:0 12px;font-size:11px;color:var(--dim);
overflow:hidden;white-space:nowrap}
footer .acc{color:var(--accent)}
footer .warn{color:var(--amber)}
footer .meter{width:110px;height:5px;background:#26272c;border-radius:3px;overflow:hidden;display:inline-block;vertical-align:middle}
footer .meter i{display:block;height:100%;background:var(--green)}
footer .right{margin-left:auto;display:flex;gap:16px}
#toast{position:fixed;bottom:40px;left:50%;transform:translateX(-50%);
background:#232428;color:var(--ink);border:1px solid var(--line);padding:7px 14px;
border-radius:8px;font-size:12.5px;display:none;z-index:9}
svg text{font-size:10px;fill:var(--dim)}
@media (max-width:1080px){body{grid-template-columns:280px 1fr}nav{display:none}footer{grid-column:1/3}}
</style></head><body>
<aside>
  <h1><span class="dot">●</span> mechanism-agent</h1>
  <div class="sub">研究机制控制台 · 台账是唯一真相<span id="ver"></span></div>
  <div class="sect">Actions</div>
  <div style="display:flex;gap:6px;flex-wrap:wrap">
    <button onclick="runCycle()">▶ 叫醒一轮</button>
    <button class="ghost" onclick="showTaskForm('leaf')">＋ 叶子</button>
    <button class="ghost" onclick="showTaskForm('ticket')">＋ 票据</button>
  </div>
  <div class="stabs" id="stabs"></div>
  <div id="side-tasks"></div>
  <div id="side-agents" style="display:none"></div>
  <div id="side-graph" style="display:none"></div>
  <form id="leaf-form" class="card" style="display:none" onsubmit="return postLeaf(event)">
    <h4>开一张叶子</h4>
    <label>编号（留空自动）</label><input name="leaf_id" placeholder="L1">
    <label>题目</label><input name="task" required placeholder="一句可判分的问题">
    <label>检查器</label><select name="checker" id="checker-sel"></select>
    <label>参数 JSON</label><input name="checker_args" placeholder='{"n": 200}'>
    <button type="submit">开题</button></form>
  <form id="ticket-form" class="card" style="display:none" onsubmit="return postTicket(event)">
    <h4>新票据</h4>
    <label>标题</label><input name="title" required>
    <label>负责人</label><input name="owner">
    <label>决定人（填 user 进等你定）</label><input name="decider">
    <label>下次触发</label><input name="next_trigger">
    <button type="submit">建票</button></form>
  <form id="agent-form" class="card" style="display:none" onsubmit="return postAgent(event)">
    <h4 id="agent-form-title">新增成员</h4>
    <label>名字</label><input name="name" required placeholder="worker-3">
    <label>角色</label><select name="role">
      <option value="worker">worker（干活）</option>
      <option value="reviewer">reviewer（复核）</option>
      <option value="coordinator">coordinator（协调）</option></select>
    <label>模型（留空 = 全局/演示后端）</label><input name="model" placeholder="gpt-… / deepseek-…">
    <label>Base URL（OpenAI 兼容端点）</label><input name="base_url" placeholder="https://…/v1">
    <label>API Key 所在环境变量名（只存名字不存 key）</label><input name="api_key_env" placeholder="MECH_AGENT_API_KEY">
    <label>Temperature</label><input name="temperature" type="number" step="0.1" min="0" max="2" value="0">
    <label><input type="checkbox" name="enabled" checked style="width:auto"> 启用</label><br>
    <button type="submit">保存成员</button>
    <button type="button" class="ghost" onclick="hideAgentForm()">取消</button></form>
</aside>
<main>
  <div class="modes" id="channels"></div>
  <div id="forkbar"></div>
  <div id="msgs"></div>
  <div id="composer"><div class="cbox">
    <textarea id="input" rows="2" placeholder="给成员发消息，或输入 /run 叫醒一轮…"></textarea>
    <div class="cfoot"><span class="pill" id="c-chan">全体</span>
    <span id="c-fork"></span>
    <span>Enter 发送 · Shift+Enter 换行 · /run /leaf /ticket /help</span>
    <span class="sp"><span id="c-model"></span><button onclick="sendChat()">发送</button></span></div>
  </div></div>
</main>
<nav>
  <h3>Prompt 导航</h3>
  <div class="dim" style="margin-bottom:8px">点任意节点：定位到那条消息并设为分叉点，下一条消息从那里长出新分支（原线保留）。</div>
  <div id="nodes"></div>
  <button class="ghost small" onclick="clearFork()" style="margin-top:8px">回到最新（取消分叉）</button>
</nav>
<footer id="statusbar"></footer>
<div id="toast"></div>
<script>
let S=null, channel="all", sideTab="tasks", forkParent=null, lastNearBottom=true;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const tm=ts=>new Date(ts*1000).toLocaleTimeString();
function toast(t){const e=$("toast");e.textContent=t;e.style.display="block";
  setTimeout(()=>e.style.display="none",3600)}
async function api(path,body){const r=await fetch(path,{method:body?"POST":"GET",
  headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);return d}
function thread(){return S.chat.filter(m=>m.channel===channel||m.channel==="all")}
function curAgent(){return S.agents.find(a=>a.name===channel)}
function render(){
  if(!S)return;
  $("ver").textContent=S.version?" · v"+S.version:"";
  $("stabs").innerHTML=[["tasks","任务"],["agents","成员"],["graph","关系图"]].map(([k,v])=>
    `<button class="${sideTab===k?"on":""}" onclick="sideTab='${k}';render()">${v}${k==="tasks"&&S.counts.decisions?`<span class="badge">${S.counts.decisions}</span>`:""}</button>`).join("");
  for(const k of["tasks","agents","graph"]) $("side-"+k).style.display=sideTab===k?"block":"none";
  const tot=S.counts.leaves_open+S.counts.leaves_closed;
  const pct=tot?Math.round(100*S.counts.leaves_closed/tot):0;
  const a=curAgent();
  $("statusbar").innerHTML=
    `<span><span class="acc">●</span> mechanism-agent${S.version?" v"+S.version:""}</span>`+
    `<span>叶子 <b>${S.counts.leaves_open}</b> 开 / <b>${S.counts.leaves_closed}</b> 关</span>`+
    `<span>进度 <span class="meter"><i style="width:${pct}%"></i></span> ${pct}%</span>`+
    `<span>票据 ${S.counts.tickets_open} 开</span>`+
    (S.counts.decisions?`<span class="warn">⏸ 等你定 ${S.counts.decisions} 件</span>`:"")+
    `<span class="right"><span>${channel==="all"?"频道 全体":"频道 "+esc(channel)}</span>`+
    `<span>模型 ${esc(a?(a.model||"全局/演示"):"—")}</span></span>`;
  $("c-chan").textContent=channel==="all"?"全体":channel;
  $("c-model").textContent=a?("模型 "+(a.model||"全局/演示")):"";
  $("c-fork").textContent=forkParent?("↳ 分叉自 #"+forkParent):"";
  renderTasks();renderAgents();renderGraph();renderChat();
}
function renderTasks(){
  const el=$("side-tasks");if(document.activeElement&&el.contains(document.activeElement)&&
    /INPUT|TEXTAREA/.test(document.activeElement.tagName))return;
  let h="";
  if(S.decisions.length){h+='<div class="sect">⏸ 等你定</div>'+S.decisions.map(t=>`
    <div class="trow dec"><div class="r1"><span style="color:var(--amber)">●</span>
    <span class="id">#${t.id}</span><span class="ttl">${esc(t.title)}</span></div>
    <div class="meta">决定人 ${esc(t.decider)} · 触发 ${esc(t.next_trigger||"—")}</div>
    <div class="act"><input id="note-${t.id}" placeholder="附言（可选）">
    <button class="small okb" onclick="decide(${t.id},'approve')">批准</button>
    <button class="small warn" onclick="decide(${t.id},'reject')">否决</button></div></div>`).join("")}
  h+='<div class="sect">认领板 · Leaves</div>'+(S.leaves.map(l=>`
    <div class="trow"><div class="r1"><span class="sdot ${l.status==="closed"?l.outcome:l.status}"></span>
    <span class="id">${esc(l.leaf_id)}</span><span class="ttl">${esc(l.task)}</span>
    <span class="tag ${l.status==="closed"?l.outcome:""}">${l.status==="closed"?l.outcome:l.status}</span></div>
    <div class="meta">${esc(l.checker||"无检查器")}${l.claimed_by?" · "+esc(l.claimed_by):""}${l.delivered_by?" → "+esc(l.delivered_by):""}${l.closed_by?" · 关 "+esc(l.closed_by):""}</div></div>`).join("")||'<div class="dim">暂无叶子</div>');
  h+='<div class="sect">票据 · Tickets</div>'+(S.tickets.map(t=>`
    <div class="trow"><div class="r1"><span class="sdot ${t.status==="closed"?"closed":"open"}"></span>
    <span class="id">#${t.id}</span><span class="ttl">${esc(t.title)}</span>
    <span class="tag">${t.status}</span></div>
    <div class="meta">负责人 ${esc(t.owner||"—")} · 决定人 ${esc(t.decider||"—")}</div>
    ${t.status!=="closed"?`<div class="act"><button class="small okb" onclick="closeTicket(${t.id},'done')">完成</button>
    <button class="small warn" onclick="closeTicket(${t.id},'dropped')">放弃</button></div>`:""}</div>`).join("")||'<div class="dim">暂无票据</div>');
  el.innerHTML=h;
}
function renderAgents(){
  const el=$("side-agents");
  el.innerHTML='<div class="sect">成员 · Agents</div>'+S.agents.map(a=>`
   <div class="trow"><div class="r1"><span class="sdot" style="background:${!a.enabled?"#484f58":a.state==="Active"?"var(--green)":"#6e7681"}"></span>
    <span class="ttl" style="flex:none">${esc(a.name)}</span><span class="tag">${a.role}</span>
    <span class="tag">${a.enabled?a.state:"停用"}</span>
    <span style="margin-left:auto;display:flex;gap:4px"><button class="small ghost" onclick='editAgent(${JSON.stringify(a.name)})'>编辑</button>
    <button class="small warn" onclick='delAgent(${JSON.stringify(a.name)})'>删除</button></span></div>
    <div class="meta">${esc(a.model||"（全局/演示）")}${a.base_url?" · "+esc(a.base_url):""} · temp ${a.temperature}</div>
    <div class="meta">认领 ${a.stats.claimed} · 交付 ${a.stats.delivered} · 关单 ${a.stats.closed}${a.last?" · 最近 "+esc(a.last):""}</div></div>`).join("")
   +'<button class="ghost" onclick="newAgent()" style="margin-top:6px">＋ 新增成员</button>';
}
function renderGraph(){
  const el=$("side-graph");const g=S.graph;
  const cx=140,cy=118,R=84;const pos={user:[cx,cy]};
  const others=g.nodes.filter(n=>n.name!=="user");
  others.forEach((n,i)=>{const t=2*Math.PI*i/Math.max(others.length,1)-Math.PI/2;
    pos[n.name]=[cx+R*Math.cos(t),cy+R*Math.sin(t)]});
  const col={dispatch:"#6e7681",deliver:"#58a6ff",close:"#4caf7d",chat:"#b083f0",reply:"#2a9f8f"};
  let s=`<div class="sect">关系图 · Graph</div><svg width="280" height="236" viewBox="0 0 280 236">`;
  for(const e of g.edges){const a=pos[e.from],b=pos[e.to];if(!a||!b)continue;
    s+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${col[e.kind]||"#555"}" stroke-width="1.3"/>
    <text x="${(a[0]+b[0])/2}" y="${(a[1]+b[1])/2-3}">${e.kind} ×${e.count}</text>`}
  for(const n of g.nodes){const p=pos[n.name];
    s+=`<circle cx="${p[0]}" cy="${p[1]}" r="15" fill="${n.name==="user"?"#d97757":"#1c1d21"}" stroke="#d97757"/>
    <text x="${p[0]}" y="${p[1]+26}" text-anchor="middle">${esc(n.name)}</text>
    <text x="${p[0]}" y="${p[1]+3}" text-anchor="middle" fill="${n.name==="user"?"#14100d":"#d97757"}">${n.name==="user"?"你":esc(n.role[0].toUpperCase())}</text>`}
  el.innerHTML=s+"</svg>"+'<div class="dim">线 = 实际发生过的交互（派工/交付/关单/对话），数字为次数。成员页可增减成员、改各自的模型参数。</div>';
}
const KINDMK={open:["●","gray","开题"],claim:["●","blue","认领"],deliver:["●","purple","交付"],
  close:["●","green","关单"],stuck:["●","amber","卡住"],release:["●","gray","释放"]};
function transcriptItems(){
  const items=thread().map(m=>({ts:m.ts,type:"chat",m}));
  if(channel==="all")for(const e of S.feed)items.push({ts:e.ts,type:"tool",e});
  return items.sort((x,y)=>x.ts-y.ts);
}
function renderChat(){
  const chans=["all",...S.agents.filter(a=>a.role!=="coordinator").map(a=>a.name)];
  if(!chans.includes(channel))channel="all";
  $("channels").innerHTML='<span class="lbl">频道</span>'+chans.map(c=>
    `<button class="${c===channel?"on":""}" onclick="channel='${c}';forkParent=null;render()">${c==="all"?"全体":c}</button>`).join("")
    +'<span class="hint">会话持久保存 · 点任意消息设为分叉点</span>';
  const items=transcriptItems();const box=$("msgs");
  const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<80;
  let prev=null;
  box.innerHTML=items.map(it=>{
    if(it.type==="tool"){const e=it.e;const k=KINDMK[e.kind]||["●","gray",e.kind||"事件"];
      return `<div class="ev"><div class="hd"><span class="mk ${k[1]}">${k[0]}</span>
      <span class="who">${k[2]} ${esc(e.leaf||"")}</span> <span class="tm">${tm(e.ts)}</span></div>
      <div class="bd res">⎿ ${e.by?"by "+esc(e.by):""}${e.outcome?' → <span class="oc">'+esc(e.outcome)+"</span>":""}</div></div>`}
    const m=it.m;const forked=m.parent_id&&prev!==null&&m.parent_id!==prev;prev=m.id;
    if(m.author==="user")return `<div class="ev user ${forkParent===m.id?"sel":""}" id="msg-${m.id}" onclick="setFork(${m.id})">
      <div class="hd"><span class="gt">&gt;</span> <span class="who">你</span> <span class="tm">#${m.id} · ${tm(m.ts)}${m.channel!=="all"&&channel==="all"?" · @"+esc(m.channel):""}</span></div>
      ${forked?`<div class="fork">↳ 分叉自 #${m.parent_id}</div>`:""}
      <div class="bd">${esc(m.text)}</div></div>`;
    const mk=m.kind==="summary"?["✻","acc"]:["●","blue"];
    return `<div class="ev ${forkParent===m.id?"sel":""}" id="msg-${m.id}" onclick="setFork(${m.id})">
      <div class="hd"><span class="mk ${mk[1]}">${mk[0]}</span> <span class="who">${esc(m.author)}</span> <span class="tm">#${m.id} · ${tm(m.ts)}</span></div>
      ${forked?`<div class="fork">↳ 分叉自 #${m.parent_id}</div>`:""}
      <div class="bd">${esc(m.text)}</div></div>`}).join("")||'<div class="dim">这个频道还没有消息，在下面发第一条（或 /run 叫醒一轮）。</div>';
  if(nearBottom||lastNearBottom)box.scrollTop=box.scrollHeight;
  lastNearBottom=nearBottom;
  const fb=$("forkbar");
  if(forkParent){fb.style.display="block";
    fb.innerHTML=`↳ 分叉点：消息 #${forkParent} — 下一条消息将从这里长出新分支。<a href="#" onclick="clearFork();return false">取消</a>`}
  else fb.style.display="none";
  $("nodes").innerHTML=thread().slice().reverse().map(m=>
    `<div class="node ${forkParent===m.id?"sel":""}" onclick="jumpTo(${m.id})">
    <span class="a">#${m.id} ${esc(m.author)}</span> ${esc(m.text.slice(0,30))}</div>`).join("");
  const sel=$("checker-sel");
  if(sel&&sel.options.length===0)sel.innerHTML='<option value="">（无检查器）</option>'+S.checkers.map(c=>`<option>${c}</option>`).join("");
}
function setFork(id){forkParent=id;render();
  const e=$("msg-"+id);if(e)e.scrollIntoView({block:"center"})}
function jumpTo(id){setFork(id)}
function clearFork(){forkParent=null;render();const b=$("msgs");b.scrollTop=b.scrollHeight}
async function sendChat(){const ta=$("input");const text=ta.value.trim();if(!text)return;
  try{
    if(text==="/help"){toast("/run 叫醒一轮 · /leaf 题目 开叶子 · /ticket 标题 建票据 · 点消息设分叉点");ta.value="";return}
    if(text==="/run"){ta.value="";runCycle();return}
    if(text.startsWith("/leaf ")){await api("/api/leaf",{task:text.slice(6)});ta.value="";toast("已开叶子");refresh();return}
    if(text.startsWith("/ticket ")){await api("/api/ticket",{title:text.slice(8)});ta.value="";toast("已建票据");refresh();return}
    await api("/api/chat",{channel,text,parent_id:forkParent});ta.value="";forkParent=null;refresh()}
  catch(e){toast("出错："+e.message)}}
$("input").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();sendChat()}});
async function runCycle(){toast("叫醒中…");try{const r=await api("/api/run",{});
  toast("本轮：证成 "+r.proven+" · 证否 "+r.refuted+" · 拆小 "+r.split);refresh()}catch(e){toast("出错："+e.message)}}
async function decide(id,decision){const n=$("note-"+id);
  try{await api("/api/decide",{ticket_id:id,decision,note:n?n.value:""});toast("决定已记录");refresh()}catch(e){toast("出错："+e.message)}}
async function closeTicket(id,reason){try{await api("/api/close-ticket",{ticket_id:id,reason});refresh()}catch(e){toast("出错："+e.message)}}
function showTaskForm(k){$("leaf-form").style.display=k==="leaf"?"block":"none";
  $("ticket-form").style.display=k==="ticket"?"block":"none";sideTab="tasks";render();
  $(k+"-form").scrollIntoView()}
async function postLeaf(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/leaf",Object.fromEntries(f));toast("已开叶子 "+r.leaf_id);
  ev.target.reset();$("leaf-form").style.display="none";refresh()}catch(e){toast("出错："+e.message)}return false}
async function postTicket(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/ticket",Object.fromEntries(f));toast("已建票 #"+r.ticket_id);
  ev.target.reset();$("ticket-form").style.display="none";refresh()}catch(e){toast("出错："+e.message)}return false}
function newAgent(){$("agent-form").style.display="block";$("agent-form-title").textContent="新增成员";
  $("agent-form").reset();sideTab="agents";render();$("agent-form").scrollIntoView()}
function editAgent(name){const a=S.agents.find(x=>x.name===name);if(!a)return;
  const f=$("agent-form");f.style.display="block";$("agent-form-title").textContent="编辑成员 "+name;
  const E=f.elements;E["name"].value=a.name;E["role"].value=a.role;E["model"].value=a.model;
  E["base_url"].value=a.base_url;E["api_key_env"].value=a.api_key_env;
  E["temperature"].value=a.temperature;E["enabled"].checked=a.enabled;
  sideTab="agents";render();f.scrollIntoView()}
async function delAgent(name){if(!confirm("删除成员 "+name+"？（历史记录保留）"))return;
  try{await api("/api/agents/delete",{name});toast("已删除 "+name);refresh()}catch(e){toast("出错："+e.message)}}
async function postAgent(ev){ev.preventDefault();const f=new FormData(ev.target);
  const rec=Object.fromEntries(f);rec.enabled=f.get("enabled")==="on";rec.temperature=parseFloat(rec.temperature||"0");
  try{await api("/api/agents",rec);toast("成员已保存："+rec.name);hideAgentForm();refresh()}catch(e){toast("出错："+e.message)}return false}
function hideAgentForm(){$("agent-form").style.display="none"}
async function refresh(){try{S=await api("/api/state");render()}catch(e){}}
refresh();setInterval(refresh,3000);
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
