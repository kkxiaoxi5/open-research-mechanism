"""End-to-end tests for the mechanism loop (mock backend, no keys).

Run:  PYTHONPATH=src python -m unittest discover -s tests -v
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mechanism_agent.agents import Reviewer, Worker  # noqa: E402
from mechanism_agent.backend import MockBackend  # noqa: E402
from mechanism_agent.board import Board  # noqa: E402
from mechanism_agent.cli import DEMO_MOCK, cmd_seed_demo  # noqa: E402
from mechanism_agent.orchestrator import Orchestrator  # noqa: E402
from mechanism_agent.tracker import Tickets  # noqa: E402


class BoardRules(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.board = Board(os.path.join(self.dir, "board.jsonl"))

    def test_illegal_outcome_rejected(self):
        self.board.open_leaf("X", "task", "exact_value", {"value": 1})
        self.board.claim("X", "w1")
        self.board.deliver("X", "w1", "1")
        with self.assertRaises(ValueError):
            self.board.close("X", "r1", "unknown")

    def test_author_cannot_close_own_leaf(self):
        self.board.open_leaf("X", "task", "exact_value", {"value": 1})
        self.board.claim("X", "w1")
        self.board.deliver("X", "w1", "1")
        with self.assertRaises(ValueError):
            self.board.close("X", "w1", "proven")

    def test_short_stuck_note_rejected(self):
        self.board.open_leaf("X", "task")
        self.board.claim("X", "w1")
        with self.assertRaises(ValueError):
            self.board.stuck("X", "w1", "stuck")


class FullLoop(unittest.TestCase):
    def test_demo_exercises_all_three_outcomes(self):
        home = tempfile.mkdtemp()
        cmd_seed_demo(home)
        board = Board(os.path.join(home, "board.jsonl"))
        tickets = Tickets(os.path.join(home, "tickets.json"))
        orch = Orchestrator(
            board, tickets,
            workers=[Worker("worker-1", MockBackend(DEMO_MOCK))],
            reviewer=Reviewer("reviewer-1"),
            snapshot_dir=os.path.join(home, "snapshot"))
        orch.cycle()
        leaves = board.leaves()
        self.assertEqual(leaves["D1"]["outcome"], "proven")
        self.assertEqual(leaves["D2"]["outcome"], "refuted")
        self.assertEqual(leaves["D3"]["outcome"], "split")
        self.assertEqual(leaves["D3.a"]["outcome"], "proven")
        self.assertEqual(leaves["D3.b"]["outcome"], "proven")
        self.assertTrue(os.path.exists(
            os.path.join(home, "snapshot", "snapshot.json")))
        self.assertEqual(len(tickets.decision_queue()), 1)


if __name__ == "__main__":
    unittest.main()
