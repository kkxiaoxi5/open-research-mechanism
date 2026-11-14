"""Read-only dashboard (standard library only).

Four views, in the order a supervisor actually reads them:
  1. Decision queue  — what is waiting on a named human;
  2. Claim board     — leaves by status and outcome;
  3. Tickets         — human-scale work;
  4. Evidence        — closed leaves grouped by outcome and evidence level.

The dashboard never writes anything; all writes go through the board,
the tracker and the orchestrator, so there is exactly one write path.
"""
from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer


def _load_snapshot(snapshot_dir: str) -> dict:
    path = os.path.join(snapshot_dir, "snapshot.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    return {"leaves": {}, "tickets": [], "decision_queue": [], "counts": {}}


def render(snapshot: dict) -> str:
    esc = html.escape
    dq = "".join(
        f"<li>#{t['id']} {esc(t['title'])} — decider: {esc(t['decider'])}; "
        f"next: {esc(t['next_trigger'])}</li>"
        for t in snapshot.get("decision_queue", [])) or "<li>(empty)</li>"
    leaves = "".join(
        f"<tr><td>{esc(lid)}</td><td>{esc(l['status'])}</td>"
        f"<td>{esc(l.get('outcome', ''))}</td><td>{esc(l.get('task', '')[:90])}</td></tr>"
        for lid, l in sorted(snapshot.get("leaves", {}).items()))
    tickets = "".join(
        f"<tr><td>#{t['id']}</td><td>{esc(t['status'])}</td>"
        f"<td>{esc(t['title'])}</td><td>{esc(t.get('owner', ''))}</td></tr>"
        for t in snapshot.get("tickets", []))
    outcomes: dict[str, int] = {}
    for leaf in snapshot.get("leaves", {}).values():
        if leaf["status"] == "closed":
            outcomes[leaf["outcome"]] = outcomes.get(leaf["outcome"], 0) + 1
    ev = "".join(f"<li>{esc(k)}: {v}</li>" for k, v in sorted(outcomes.items())) \
        or "<li>(nothing closed yet)</li>"
    return f"""<!doctype html><meta charset="utf-8">
<title>Mechanism dashboard</title>
<meta http-equiv="refresh" content="30">
<style>body{{font-family:system-ui;margin:2rem;max-width:60rem}}
table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:.3rem .6rem}}</style>
<h1>Mechanism dashboard</h1>
<h2>1 · Waiting for a decision</h2><ul>{dq}</ul>
<h2>2 · Claim board</h2><table><tr><th>leaf</th><th>status</th><th>outcome</th><th>task</th></tr>{leaves}</table>
<h2>3 · Tickets</h2><table><tr><th>#</th><th>status</th><th>title</th><th>owner</th></tr>{tickets}</table>
<h2>4 · Evidence (closed leaves by outcome)</h2><ul>{ev}</ul>
"""


def serve(snapshot_dir: str, host: str = "127.0.0.1", port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - stdlib handler API
            body = render(_load_snapshot(snapshot_dir)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):  # keep the console quiet
            pass

    HTTPServer((host, port), Handler).serve_forever()
