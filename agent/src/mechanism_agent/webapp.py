"""Interactive web UI for mechanism-agent.

This is the user's operating surface (PLAN decision: the UI is a
required, interactive part of the system — not a read-only report).
It offers five views — decision queue, claim board, tickets, members,
activity — and five actions: open a leaf, open a ticket, decide a
decision ticket, message a member, and run one wake-up cycle.

Discipline is preserved: the web layer never writes state files
directly. Every action goes through the same Board / Tickets /
Orchestrator classes the CLI uses, so the board's rules (three
outcomes, no self-closing, stuck notes) bind the UI exactly as they
bind the agents. There is no login in this reference build; it is
meant for a trusted local network (see PLAN.md).
"""
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agents import CHECKERS, Reviewer, Worker
from .backend import backend_from_env
from .board import Board
from .orchestrator import Orchestrator
from .skills import prompt_block
from .tracker import Tickets

ROSTER = ("coordinator", "worker-1", "worker-2", "reviewer-1")


class Inbox:
    """User -> member direct messages (JSONL, append-only)."""

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
        self.snapshot_dir = os.path.join(home, "snapshot")

    # -- state ---------------------------------------------------------
    def state(self) -> dict:
        leaves = self.board.leaves()
        tickets = self.tickets.all()
        feed = []
        for ev in self.board._events():
            feed.append({"ts": ev.get("ts", 0), "kind": ev.get("kind"),
                         "leaf": ev.get("leaf_id"), "by": ev.get("by"),
                         "outcome": ev.get("outcome")})
        for m in self.inbox.all():
            feed.append({"ts": m["ts"], "kind": "message",
                         "leaf": None, "by": "user",
                         "outcome": f"→ {m['to']}: {m['text'][:60]}"})
        feed.sort(key=lambda e: e["ts"], reverse=True)
        members = {}
        for name in ROSTER:
            members[name] = {"name": name, "state": "Waiting",
                             "doing": "", "last": ""}
        for leaf in leaves.values():
            if leaf["status"] == "claimed" and leaf.get("claimed_by") in members:
                members[leaf["claimed_by"]].update(
                    state="Active", doing=f"working on {leaf['leaf_id']}")
            if leaf["status"] == "delivered" and leaf.get("delivered_by") in members:
                members[leaf["delivered_by"]]["last"] = \
                    f"delivered {leaf['leaf_id']}"
            if leaf.get("closed_by") in members:
                members[leaf["closed_by"]]["last"] = \
                    f"closed {leaf['leaf_id']} as {leaf.get('outcome')}"
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
            "members": list(members.values()),
            "feed": feed[:40],
            "checkers": sorted(CHECKERS),
        }

    # -- actions ---------------------------------------------------------
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
        reason = data.get("reason", "done")
        self.tickets.set_status(tid, "closed", by="user", reason=reason)
        return {"ticket_id": tid, "closed_as": reason}

    def message(self, data: dict) -> dict:
        return self.inbox.post(data.get("to", "*"), data["text"])

    def run_cycle(self) -> dict:
        from .cli import DEMO_MOCK
        backend = backend_from_env(DEMO_MOCK)
        workers = []
        for name in ("worker-1", "worker-2"):
            extra = ""
            pending = self.inbox.pending_for(name)
            if pending:
                extra = "\n\nDirect messages from the user:\n" + "\n".join(
                    f"- {m['text']}" for m in pending)
                self.inbox.mark_delivered(name)
            workers.append(Worker(name, backend,
                                  prompt_block("worker") + extra))
        orch = Orchestrator(self.board, self.tickets, workers=workers,
                            reviewer=Reviewer("reviewer-1"),
                            snapshot_dir=self.snapshot_dir)
        return orch.cycle()


PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>mechanism-agent 控制台</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--line:#e3e6ea;--ink:#1c2330;--dim:#68707d;
--green:#177245;--red:#b3372f;--amber:#9a6a00;--blue:#2456a6}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:14px/1.55 -apple-system,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif}
header{background:#141a24;color:#eef1f5;padding:14px 20px;display:flex;
flex-wrap:wrap;gap:10px;align-items:center}
header h1{font-size:17px;margin:0;font-weight:650}
header .sub{color:#9fb0c3;font-size:12px}
.counts{margin-left:auto;display:flex;gap:14px;font-size:13px;color:#cfe0f2}
.counts b{font-size:16px;color:#fff}
button{background:var(--blue);color:#fff;border:0;border-radius:7px;
padding:7px 13px;cursor:pointer;font-size:13px}
button.ghost{background:#2a3444}button.small{padding:3px 9px;font-size:12px}
button.warn{background:var(--red)}button.ok{background:var(--green)}
nav{display:flex;gap:4px;padding:10px 20px 0}
nav button{background:none;color:var(--dim);border-bottom:2px solid transparent;
border-radius:0;padding:6px 10px}
nav button.on{color:var(--ink);border-bottom-color:var(--blue);font-weight:600}
.badge{background:var(--red);color:#fff;border-radius:9px;padding:0 6px;
font-size:11px;margin-left:4px}
main{padding:14px 20px 30px;max-width:1060px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:12px 14px;margin:0 0 10px}
.card h3{margin:0 0 4px;font-size:14px}
.dim{color:var(--dim);font-size:12px}
.chip{border-radius:9px;padding:0 8px;font-size:11px;color:#fff}
.proven{background:var(--green)}.refuted{background:var(--red)}
.split{background:var(--amber)}.open{background:#5b6b80}
.claimed{background:var(--blue)}.delivered{background:#6a4fa3}
.closed{background:#39424f}
.row{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.row .sp{margin-left:auto;display:flex;gap:6px}
input,select,textarea{border:1px solid var(--line);border-radius:7px;
padding:7px 9px;font:inherit;width:100%;margin:3px 0 9px;background:#fff}
label{font-size:12px;color:var(--dim)}
.panel{display:none}.panel.on{display:block}
form.card{max-width:560px}
.feed div{padding:5px 0;border-bottom:1px dashed var(--line)}
footer{color:var(--dim);font-size:12px;padding:0 20px 22px}
</style></head><body>
<header>
  <div><h1>mechanism-agent 控制台</h1>
  <div class="sub">认领板 · 票据 · 决定队列 — 所有操作经服务端的板规校验写入</div></div>
  <div class="counts">
    <span>叶子开 <b id="c-open">–</b></span>
    <span>已关 <b id="c-closed">–</b></span>
    <span>票据 <b id="c-tickets">–</b></span>
    <span>等你定 <b id="c-dec">–</b></span>
  </div>
  <button onclick="runCycle()">▶ 叫醒一轮</button>
  <button class="ghost" onclick="showForm('leaf-form')">＋ 开叶子</button>
  <button class="ghost" onclick="showForm('ticket-form')">＋ 新票据</button>
</header>
<nav id="tabs"></nav>
<main>
  <section id="tab-decisions" class="panel"></section>
  <section id="tab-board" class="panel"></section>
  <section id="tab-tickets" class="panel"></section>
  <section id="tab-members" class="panel"></section>
  <section id="tab-feed" class="panel"></section>

  <form id="leaf-form" class="card" style="display:none" onsubmit="return postLeaf(event)">
    <h3>开一张叶子</h3>
    <label>叶子编号（留空自动 L 编号）</label><input name="leaf_id" placeholder="L1">
    <label>题目（一句可判分的问题）</label><input name="task" required placeholder="例如：1 到 200 的整数和">
    <label>检查器</label><select name="checker" id="checker-sel"></select>
    <label>检查器参数（JSON，可空）</label><input name="checker_args" placeholder='{"n": 200}'>
    <button type="submit">开题</button>
    <button type="button" class="ghost" onclick="hideForms()">取消</button>
  </form>

  <form id="ticket-form" class="card" style="display:none" onsubmit="return postTicket(event)">
    <h3>新票据</h3>
    <label>标题</label><input name="title" required>
    <label>负责人（可空）</label><input name="owner">
    <label>决定人（填了就进「等你定」，如 user）</label><input name="decider">
    <label>下次触发条件（可空）</label><input name="next_trigger">
    <button type="submit">建票</button>
    <button type="button" class="ghost" onclick="hideForms()">取消</button>
  </form>

  <form id="msg-form" class="card" style="display:none" onsubmit="return postMsg(event)">
    <h3>给成员发消息</h3>
    <label>收件人</label><select name="to" id="msg-to"></select>
    <label>内容</label><textarea name="text" rows="3" required></textarea>
    <button type="submit">发送（下一轮叫醒时送达）</button>
    <button type="button" class="ghost" onclick="hideForms()">取消</button>
  </form>
  <div id="toast" class="dim"></div>
</main>
<footer>参考实现：无登录，请只在可信内网运行（见 agent/PLAN.md）。台账（board.jsonl）是唯一真相，页面只是它的操作面。</footer>
<script>
const TABS=[["decisions","等你定"],["board","认领板"],["tickets","票据"],
["members","成员"],["feed","动态"]];
let cur="decisions", S=null;
const $=id=>document.getElementById(id);
function esc(s){return String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]))}
function toast(t){$("toast").textContent=t;setTimeout(()=>$("toast").textContent="",4000)}
async function api(path,body){
  const r=await fetch(path,{method:body?"POST":"GET",
    headers:{"Content-Type":"application/json"},
    body:body?JSON.stringify(body):undefined});
  const d=await r.json(); if(!r.ok) throw new Error(d.error||r.status); return d}
function showForm(id){hideForms();$(id).style.display="block"}
function hideForms(){for(const f of["leaf-form","ticket-form","msg-form"])$(f).style.display="none"}
function switchTab(t){cur=t;render()}
function render(){
  if(!S)return;
  $("c-open").textContent=S.counts.leaves_open;
  $("c-closed").textContent=S.counts.leaves_closed;
  $("c-tickets").textContent=S.counts.tickets_open;
  $("c-dec").textContent=S.counts.decisions;
  $("tabs").innerHTML=TABS.map(([k,v])=>`<button class="${k===cur?"on":""}"
    onclick="switchTab('${k}')">${v}${k==="decisions"&&S.counts.decisions?`<span class="badge">${S.counts.decisions}</span>`:""}</button>`).join("");
  for(const [k] of TABS) $("tab-"+k).classList.toggle("on",k===cur);
  $("tab-decisions").innerHTML=S.decisions.length?S.decisions.map(t=>`
    <div class="card"><h3>#${t.id} ${esc(t.title)}</h3>
    <div class="dim">决定人：${esc(t.decider)} · 下次触发：${esc(t.next_trigger||"—")}</div>
    <div class="row" style="margin-top:8px"><input id="note-${t.id}" placeholder="决定附言（可选）" style="flex:1">
    <span class="sp"><button class="ok" onclick="decide(${t.id},'approve')">批准并关票</button>
    <button class="warn" onclick="decide(${t.id},'reject')">否决并关票</button></span></div></div>`).join("")
    :'<div class="card">没有等你定的事项。</div>';
  $("tab-board").innerHTML=S.leaves.map(l=>`
    <div class="card"><div class="row"><b>${esc(l.leaf_id)}</b>
    <span class="chip ${l.status==="closed"?l.outcome:l.status}">${l.status==="closed"?l.outcome:l.status}</span>
    ${l.parent?`<span class="dim">父叶 ${esc(l.parent)}</span>`:""}
    <span class="dim">${esc(l.checker||"无检查器")}</span></div>
    <div>${esc(l.task)}</div>
    <div class="dim">${l.claimed_by?"认领："+esc(l.claimed_by):""}
    ${l.delivered_by?"交付："+esc(l.delivered_by)+" → "+esc(l.answer||""):""}
    ${l.closed_by?"关单："+esc(l.closed_by)+" · "+esc(l.verdict||""):""}</div></div>`).join("")
    ||'<div class="card">板上还没有叶子。</div>';
  $("tab-tickets").innerHTML=S.tickets.map(t=>`
    <div class="card"><div class="row"><b>#${t.id}</b><span>${esc(t.title)}</span>
    <span class="chip ${t.status==="closed"?"closed":"open"}">${t.status}</span>
    ${t.status!=="closed"?`<span class="sp">
      <button class="small ok" onclick="closeTicket(${t.id},'done')">完成</button>
      <button class="small warn" onclick="closeTicket(${t.id},'dropped')">放弃</button></span>`:""}
    </div><div class="dim">负责人 ${esc(t.owner||"—")} · 决定人 ${esc(t.decider||"—")} · 触发 ${esc(t.next_trigger||"—")}</div></div>`).join("")
    ||'<div class="card">还没有票据。</div>';
  $("tab-members").innerHTML=S.members.map(m=>`
    <div class="card"><div class="row"><b>${esc(m.name)}</b>
    <span class="chip ${m.state==="Active"?"claimed":"open"}">${m.state}</span>
    <span class="sp"><button class="small" onclick="msgTo('${esc(m.name)}')">发消息</button></span></div>
    <div class="dim">${esc(m.doing||"")} ${esc(m.last||"")}</div></div>`).join("");
  $("msg-to").innerHTML=S.members.map(m=>`<option>${esc(m.name)}</option>`).join("")+'<option value="*">全体</option>';
  $("tab-feed").innerHTML='<div class="card feed">'+S.feed.map(e=>`
    <div><span class="dim">${new Date(e.ts*1000).toLocaleTimeString()}</span>
    ${esc(e.kind)} ${e.leaf?"· "+esc(e.leaf):""} ${e.by?"· "+esc(e.by):""}
    ${e.outcome?"· "+esc(e.outcome):""}</div>`).join("")+"</div>";
  const sel=$("checker-sel");
  if(sel.options.length===0){sel.innerHTML='<option value="">（无检查器）</option>'+
    S.checkers.map(c=>`<option>${c}</option>`).join("")}
}
async function refresh(){try{S=await api("/api/state");render()}catch(e){}}
async function runCycle(){toast("叫醒中…");try{const r=await api("/api/run",{});
  toast("本轮：证成 "+r.proven+" · 证否 "+r.refuted+" · 拆小 "+r.split);refresh()}catch(e){toast("出错："+e.message)}}
async function decide(id,decision){const note=$("note-"+id).value;
  try{await api("/api/decide",{ticket_id:id,decision,note});toast("已记录决定");refresh()}catch(e){toast("出错："+e.message)}}
async function closeTicket(id,reason){try{await api("/api/close-ticket",{ticket_id:id,reason});
  toast("票据已关");refresh()}catch(e){toast("出错："+e.message)}}
function msgTo(name){showForm("msg-form");$("msg-to").value=name}
async function postLeaf(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/leaf",Object.fromEntries(f));toast("已开叶子 "+r.leaf_id);
  hideForms();ev.target.reset();refresh()}catch(e){toast("出错："+e.message)}return false}
async function postTicket(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{const r=await api("/api/ticket",Object.fromEntries(f));toast("已建票 #"+r.ticket_id);
  hideForms();ev.target.reset();refresh()}catch(e){toast("出错："+e.message)}return false}
async function postMsg(ev){ev.preventDefault();const f=new FormData(ev.target);
  try{await api("/api/message",Object.fromEntries(f));toast("消息已排队，下一轮送达");
  hideForms();ev.target.reset();refresh()}catch(e){toast("出错："+e.message)}return false}
refresh();setInterval(refresh,3000);
</script></body></html>
"""


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep stdout clean
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
                          "/api/message": app.message}
                if self.path == "/api/run":
                    self._json(200, app.run_cycle())
                elif self.path in routes:
                    self._json(200, routes[self.path](data))
                else:
                    self._json(404, {"error": "not found"})
            except Exception as exc:  # board/ticket rule violations land here
                self._json(400, {"error": str(exc)})

    return Handler


def serve(home: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    app = App(home)
    ThreadingHTTPServer((host, port), make_handler(app)).serve_forever()
