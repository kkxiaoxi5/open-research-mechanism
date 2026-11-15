import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from mechanism_agent import cli
from mechanism_agent.webapp import App, make_handler


class WebApp(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.home = tempfile.mkdtemp()
        cli.cmd_init(self.home)
        cli.cmd_seed_demo(self.home)
        self.app = App(self.home)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0),
                                          make_handler(self.app))
        self.port = self.server.server_address[1]
        threading.Thread(target=self.server.serve_forever,
                         daemon=True).start()

    def tearDown(self):
        self.server.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
            method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_page_and_state(self):
        with urllib.request.urlopen(
                f"http://127.0.0.1:{self.port}/") as resp:
            html = resp.read().decode()
        self.assertIn("mechanism-agent console", html)
        self.assertIn("mech-lang", html)  # EN/JA UI switch
        _, state = self.call("/api/state")
        self.assertEqual(state["counts"]["decisions"], 1)
        self.assertEqual(len(state["agents"]), 4)

    def test_open_leaf_run_and_decide(self):
        _, r = self.call("/api/leaf", {"task": "Sum 1 to 10",
                                       "checker": "sum_to_n",
                                       "checker_args": {"n": 10}})
        self.assertEqual(r["leaf_id"], "L1")
        _, log = self.call("/api/run", {})
        self.assertIn("counts", log)
        _, state = self.call("/api/state")
        closed = {l["leaf_id"]: l.get("outcome") for l in state["leaves"]
                  if l["status"] == "closed"}
        self.assertEqual(closed.get("D1"), "proven")
        self.assertEqual(closed.get("D2"), "refuted")
        self.assertEqual(closed.get("D3"), "split")
        tid = state["decisions"][0]["id"]
        _, r = self.call("/api/decide", {"ticket_id": tid,
                                         "decision": "approve",
                                         "note": "go"})
        self.assertEqual(r["closed_as"], "done")
        _, state = self.call("/api/state")
        self.assertEqual(state["counts"]["decisions"], 0)

    def test_agents_registry_chat_and_graph(self):
        _, r = self.call("/api/agents", {"name": "worker-3", "role": "worker",
                                         "model": "m-x", "temperature": 0.7})
        self.assertEqual(r["name"], "worker-3")
        _, state = self.call("/api/state")
        self.assertEqual(len(state["agents"]), 5)
        w3 = [a for a in state["agents"] if a["name"] == "worker-3"][0]
        self.assertEqual(w3["model"], "m-x")
        self.assertEqual(w3["temperature"], 0.7)
        # chat: post, fork from it, run a cycle -> the agent replies
        _, m1 = self.call("/api/chat", {"channel": "worker-1",
                                        "text": "please focus"})
        _, m2 = self.call("/api/chat", {"channel": "worker-1",
                                        "text": "branching from first",
                                        "parent_id": m1["id"]})
        self.assertEqual(m2["parent_id"], m1["id"])
        self.call("/api/run", {})
        _, state = self.call("/api/state")
        authors = [m["author"] for m in state["chat"]]
        self.assertIn("worker-1", authors)       # reply was posted
        self.assertIn("coordinator", authors)    # cycle summary was posted
        kinds = {(e["from"], e["to"]) for e in state["graph"]["edges"]}
        self.assertIn(("user", "worker-1"), kinds)
        # delete the extra agent again
        _, r = self.call("/api/agents/delete", {"name": "worker-3"})
        self.assertEqual(r["removed"], "worker-3")
        _, state = self.call("/api/state")
        self.assertEqual(len(state["agents"]), 4)

    def test_message_and_rule_violation(self):
        self.app.message({"to": "worker-1", "text": "focus on D2"})
        self.assertEqual(len(self.app.inbox.pending_for("worker-1")), 1)
        code, r = self.call("/api/leaf", {"task": "x", "checker": "nope"})
        self.assertEqual(code, 400)
        self.assertIn("unknown checker", r["error"])


if __name__ == "__main__":
    unittest.main()
