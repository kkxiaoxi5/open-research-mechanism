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
        self.assertIn("控制台", html)
        _, state = self.call("/api/state")
        self.assertEqual(state["counts"]["decisions"], 1)
        self.assertEqual(len(state["members"]), 4)

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

    def test_message_and_rule_violation(self):
        self.app.message({"to": "worker-1", "text": "focus on D2"})
        self.assertEqual(len(self.app.inbox.pending_for("worker-1")), 1)
        code, r = self.call("/api/leaf", {"task": "x", "checker": "nope"})
        self.assertEqual(code, 400)
        self.assertIn("unknown checker", r["error"])


if __name__ == "__main__":
    unittest.main()
