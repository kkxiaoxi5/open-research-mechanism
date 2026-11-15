"""Interactive web console for mechanism-agent.

The user's operating surface (PLAN decision: the UI is a required,
interactive part of the system). Layout: a task-management sidebar
(decision queue / claim board / tickets / agent management / relation
graph), a persistent chat pane with per-agent channels, and a prompt
navigator that selects any message as a fork point so a conversation
can branch from any position.

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
:root{--bg:#eef0f3;--panel:#fff;--line:#e0e4ea;--ink:#1b2330;--dim:#68707d;
--green:#177245;--red:#b3372f;--amber:#9a6a00;--blue:#2456a6;--purple:#6a4fa3}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);display:grid;
grid-template-columns:344px 1fr 236px;height:100vh;
font:14px/1.55 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
aside{background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;
padding:14px 14px 20px}
aside h1{font-size:16px;margin:0}
.sub{color:var(--dim);font-size:12px}
.counts{display:flex;gap:12px;margin:10px 0;font-size:12px;color:var(--dim)}
.counts b{color:var(--ink);font-size:15px}
button{background:var(--blue);color:#fff;border:0;border-radius:7px;
padding:6px 12px;cursor:pointer;font-size:13px}
button.ghost{background:#eef1f5;color:var(--ink)}
button.small{padding:2px 8px;font-size:12px}
button.warn{background:var(--red)}button.ok{background:var(--green)}
.stabs{display:flex;gap:4px;margin:12px 0 8px}
.stabs button{background:none;color:var(--dim);border-bottom:2px solid transparent;
border-radius:0;padding:4px 8px}
.stabs button.on{color:var(--ink);border-bottom-color:var(--blue);font-weight:600}
.badge{background:var(--red);color:#fff;border-radius:9px;padding:0 6px;
font-size:11px;margin-left:4px}
.card{border:1px solid var(--line);border-radius:9px;padding:9px 11px;margin:0 0 8px}
.card h4{margin:0 0 2px;font-size:13px}
.dim{color:var(--dim);font-size:12px}
.chip{border-radius:9px;padding:0 7px;font-size:11px;color:#fff;white-space:nowrap}
.proven{background:var(--green)}.refuted{background:var(--red)}
.split{background:var(--amber)}.open{background:#5b6b80}
.claimed{background:var(--blue)}.delivered{background:var(--purple)}
.closed{background:#39424f}.role{background:#8892a0}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.row .sp{margin-left:auto;display:flex;gap:5px}
input,select,textarea{border:1px solid var(--line);border-radius:7px;
padding:6px 8px;font:inherit;width:100%;margin:2px 0 8px;background:#fff}
label{font-size:12px;color:var(--dim)}
main{display:flex;flex-direction:column;min-width:0;background:#f7f8fa}
.channels{display:flex;gap:6px;padding:10px 14px;border-bottom:1px solid var(--line);
background:var(--panel);flex-wrap:wrap;align-items:center}
.channels button{background:#eef1f5;color:var(--ink)}
.channels button.on{background:var(--blue);color:#fff}
#forkbar{display:none;background:#fff7e0;border-bottom:1px solid #ecd9a0;
padding:6px 14px;font-size:12px}
#msgs{flex:1;overflow-y:auto;padding:14px}
.msg{max-width:78%;margin:0 0 10px;padding:8px 12px;border-radius:12px;
background:#fff;border:1px solid var(--line);cursor:pointer}
.msg.user{margin-left:auto;background:#dcebfd;border-color:#bcd4f5}
.msg.summary{margin:0 auto 10px;background:#f0ead8;max-width:88%;text-align:left}
.msg.sel{outline:2px solid var(--amber)}
.msg .meta{font-size:11px;color:var(--dim);margin-bottom:2px}
.msg .fork{color:var(--amber);font-size:11px}
#composer{display:flex;gap:8px;padding:10px 14px;background:var(--panel);
border-top:1px solid var(--line)}
#composer textarea{flex:1;margin:0;resize:none}
nav{background:var(--panel);border-left:1px solid var(--line);overflow-y:auto;
padding:14px 10px}
nav h3{font-size:13px;margin:0 0 8px}
.node{padding:6px 8px;border-radius:7px;cursor:pointer;font-size:12px;
border:1px solid transparent}
.node:hover{background:#f2f4f7}
.node.sel{border-color:var(--amber);background:#fff7e0}
.node .a{color:var(--dim)}
#toast{position:fixed;bottom:14px;left:50%;transform:translateX(-50%);
background:#141a24;color:#eef1f5;padding:7px 14px;border-radius:8px;
font-size:13px;display:none;z-index:9}
svg text{font-size:10px;fill:var(--ink)}
@media (max-width:1080px){body{grid-template-columns:300px 1fr}nav{display:none}}
</style></head><body>
<aside>
  <h1>mechanism-agent</h1>
  <div class="sub">研究机制控制台 · 写入经 Board/Tickets 规则校验</div>
  <div class="counts"><span>叶子开 <b id="c-open">–</b></span>
  <span>已关 <b id="c-closed">–</b></span><span>票据 <b id="c-tix">–</b></span>
  <span>等你定 <b id="c-dec">–</b></span></div>
  <div class="row"><button onclick="runCycle()">▶ 叫醒一轮</button>
  <button class="ghost" onclick="showTaskForm('leaf')">＋ 开叶子</button>
  <button class="ghost" onclick="showTaskForm('ticket')">＋ 新票据</button></div>
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
  <div class="channels" id="channels"></div>
  <div id="forkbar"></div>
  <div id="msgs"></div>
  <div id="composer">
    <textarea id="input" rows="2" placeholder="发消息…（Enter 发送，Shift+Enter 换行）"></textarea>
    <button onclick="sendChat()">发送</button>
  </div>
</main>
<nav>
  <h3>Prompt 导航</h3>
  <div class="dim" style="margin-bottom:8px">点任意节点：定位到那条消息并设为分叉点，下一条消息将从那里长出新分支（原线保留）。</div>
  <div id="nodes"></div>
  <button class="ghost small" onclick="clearFork()" style="margin-top:8px">回到最新（取消分叉）</button>
</nav>
<div id="toast"></div>
<script>
let S=null, channel="all", sideTab="tasks", forkParent=null, lastNearBottom=true;
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function toast(t){const e=$("toast");e.textContent=t;e.style.display="block";
  setTimeout(()=>e.style.display="none",3600)}
async function api(path,body){const r=await fetch(path,{method:body?"POST":"GET",
  headers:{"Content-Type":"application/json"},body:body?JSON.stringify(body):undefined});
  const d=await r.json();if(!r.ok)throw new Error(d.error||r.status);return d}
function thread(){return S.chat.filter(m=>m.channel===channel||m.channel==="all")}
function render(){
  if(!S)return;
  $("c-open").textContent=S.counts.leaves_open;$("c-closed").textContent=S.counts.leaves_closed;
  $("c-tix").textContent=S.counts.tickets_open;$("c-dec").textContent=S.counts.decisions;
  $("stabs").innerHTML=[["tasks","任务"],["agents","成员"],["graph","关系图"]].map(([k,v])=>
    `<button class="${sideTab===k?"on":""}" onclick="sideTab='${k}';render()">${v}${k==="tasks"&&S.counts.decisions?`<span class="badge">${S.counts.decisions}</span>`:""}</button>`).join("");
  for(const k of["tasks","agents","graph"]) $("side-"+k).style.display=sideTab===k?"block":"none";
  renderTasks();renderAgents();renderGraph();renderChat();
}
function renderTasks(){
  const el=$("side-tasks");if(document.activeElement&&el.contains(document.activeElement)&&
    /INPUT|TEXTAREA/.test(document.activeElement.tagName))return;
  let h="";
  if(S.decisions.length){h+="<h4>等你定</h4>"+S.decisions.map(t=>`
    <div class="card"><h4>#${t.id} ${esc(t.title)}</h4>
    <div class="dim">决定人 ${esc(t.decider)} · 触发 ${esc(t.next_trigger||"—")}</div>
    <div class="row" style="margin-top:6px"><input id="note-${t.id}" placeholder="附言（可选）">
    <span class="sp"><button class="small ok" onclick="decide(${t.id},'approve')">批准</button>
    <button class="small warn" onclick="decide(${t.id},'reject')">否决</button></span></div></div>`).join("")}
  h+="<h4>认领板</h4>"+(S.leaves.map(l=>`
    <div class="card"><div class="row"><b>${esc(l.leaf_id)}</b>
    <span class="chip ${l.status==="closed"?l.outcome:l.status}">${l.status==="closed"?l.outcome:l.status}</span>
    <span class="dim">${esc(l.checker||"")}</span></div>
    <div style="font-size:13px">${esc(l.task)}</div>
    <div class="dim">${l.claimed_by?"认领 "+esc(l.claimed_by):""} ${l.delivered_by?"· 交付 "+esc(l.delivered_by):""} ${l.closed_by?"· 关单 "+esc(l.closed_by):""}</div></div>`).join("")||'<div class="dim">暂无叶子</div>');
  h+="<h4>票据</h4>"+(S.tickets.map(t=>`
    <div class="card"><div class="row"><b>#${t.id}</b><span style="font-size:13px">${esc(t.title)}</span>
    <span class="chip ${t.status==="closed"?"closed":"open"}">${t.status}</span>
    ${t.status!=="closed"?`<span class="sp"><button class="small ok" onclick="closeTicket(${t.id},'done')">完成</button>
    <button class="small warn" onclick="closeTicket(${t.id},'dropped')">放弃</button></span>`:""}</div>
    <div class="dim">负责人 ${esc(t.owner||"—")} · 决定人 ${esc(t.decider||"—")}</div></div>`).join("")||'<div class="dim">暂无票据</div>');
  el.innerHTML=h;
}
function renderAgents(){
  const el=$("side-agents");
  el.innerHTML=S.agents.map(a=>`
   <div class="card"><div class="row"><b>${esc(a.name)}</b>
    <span class="chip role">${a.role}</span>
    <span class="chip ${a.state==="Active"?"claimed":"open"}">${a.enabled?a.state:"停用"}</span>
    <span class="sp"><button class="small ghost" onclick='editAgent(${JSON.stringify(a.name)})'>编辑</button>
    <button class="small warn" onclick='delAgent(${JSON.stringify(a.name)})'>删除</button></span></div>
    <div class="dim">模型 ${esc(a.model||"（全局/演示）")} ${a.base_url?"· "+esc(a.base_url):""} · temp ${a.temperature}</div>
    <div class="dim">认领 ${a.stats.claimed} · 交付 ${a.stats.delivered} · 关单 ${a.stats.closed}${a.last?" · 最近 "+esc(a.last):""}</div></div>`).join("")
   +'<button onclick="newAgent()">＋ 新增成员</button>';
}
function renderGraph(){
  const el=$("side-graph");const g=S.graph;
  const cx=150,cy=125,R=92;const pos={user:[cx,cy]};
  const others=g.nodes.filter(n=>n.name!=="user");
  others.forEach((n,i)=>{const t=2*Math.PI*i/Math.max(others.length,1)-Math.PI/2;
    pos[n.name]=[cx+R*Math.cos(t),cy+R*Math.sin(t)]});
  const col={dispatch:"#8892a0",deliver:"#2456a6",close:"#177245",chat:"#6a4fa3",reply:"#2a7f8f"};
  let s=`<svg width="300" height="250" viewBox="0 0 300 250">`;
  for(const e of g.edges){const a=pos[e.from],b=pos[e.to];if(!a||!b)continue;
    s+=`<line x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}" stroke="${col[e.kind]||"#999"}" stroke-width="1.4"/>
    <text x="${(a[0]+b[0])/2}" y="${(a[1]+b[1])/2-3}">${e.kind} ×${e.count}</text>`}
  for(const n of g.nodes){const p=pos[n.name];
    s+=`<circle cx="${p[0]}" cy="${p[1]}" r="17" fill="${n.name==="user"?"#2456a6":"#fff"}" stroke="#2456a6"/>
    <text x="${p[0]}" y="${p[1]+28}" text-anchor="middle">${esc(n.name)}</text>
    <text x="${p[0]}" y="${p[1]+3}" text-anchor="middle" fill="${n.name==="user"?"#fff":"#2456a6"}">${n.name==="user"?"你":esc(n.role[0].toUpperCase())}</text>`}
  el.innerHTML=s+"</svg>"+'<div class="dim">线 = 实际发生过的交互（派工/交付/关单/对话），数字为次数。点成员卡片的编辑可改模型参数。</div>';
}
function renderChat(){
  const chans=["all",...S.agents.filter(a=>a.role!=="coordinator").map(a=>a.name)];
  if(!chans.includes(channel))channel="all";
  $("channels").innerHTML='<span class="dim">频道</span>'+chans.map(c=>
    `<button class="${c===channel?"on":""}" onclick="channel='${c}';forkParent=null;render()">${c==="all"?"全体":c}</button>`).join("")
    +'<span class="dim" style="margin-left:auto">会话持久保存 · 可从任意消息分叉</span>';
  const th=thread();const box=$("msgs");
  const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<80;
  let prev=null;
  box.innerHTML=th.map(m=>{const forked=m.parent_id&&prev!==null&&m.parent_id!==prev;
    prev=m.id;return `<div class="msg ${m.author==="user"?"user":m.kind==="summary"?"summary":""} ${forkParent===m.id?"sel":""}" id="msg-${m.id}" onclick="setFork(${m.id})">
    <div class="meta">#${m.id} ${esc(m.author)} · ${new Date(m.ts*1000).toLocaleTimeString()}${m.channel!=="all"&&channel==="all"?" · @"+esc(m.channel):""}</div>
    ${forked?`<div class="fork">↳ 分叉自 #${m.parent_id}</div>`:""}
    <div>${esc(m.text)}</div></div>`}).join("")||'<div class="dim">这个频道还没有消息，在下面发第一条。</div>';
  if(nearBottom||lastNearBottom)box.scrollTop=box.scrollHeight;
  lastNearBottom=nearBottom;
  const fb=$("forkbar");
  if(forkParent){fb.style.display="block";
    fb.innerHTML=`分叉点：消息 #${forkParent} — 下一条消息将从这里长出新分支。<a href="#" onclick="clearFork();return false">取消</a>`}
  else fb.style.display="none";
  $("nodes").innerHTML=[...th].reverse().map(m=>
    `<div class="node ${forkParent===m.id?"sel":""}" onclick="jumpTo(${m.id})">
    <span class="a">#${m.id} ${esc(m.author)}</span> ${esc(m.text.slice(0,34))}</div>`).join("");
  const sel=$("checker-sel");
  if(sel&&sel.options.length===0)sel.innerHTML='<option value="">（无检查器）</option>'+S.checkers.map(c=>`<option>${c}</option>`).join("");
}
function setFork(id){forkParent=id;render();
  const e=$("msg-"+id);if(e)e.scrollIntoView({block:"center"})}
function jumpTo(id){setFork(id)}
function clearFork(){forkParent=null;render();const b=$("msgs");b.scrollTop=b.scrollHeight}
async function sendChat(){const ta=$("input");const text=ta.value.trim();if(!text)return;
  try{await api("/api/chat",{channel,text,parent_id:forkParent});ta.value="";forkParent=null;refresh()}
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
</script></body></html>
"""


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


def serve(home: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = App(home)
    ThreadingHTTPServer((host, port), make_handler(app)).serve_forever()
