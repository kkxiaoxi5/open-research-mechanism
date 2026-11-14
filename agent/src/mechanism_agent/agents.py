"""Worker and reviewer agents, plus the known-answer checker registry.

The loop's honesty comes from one asymmetry: the worker *proposes* an
answer, the reviewer *recomputes* it with a checker that does not depend
on the worker's reasoning. Checkers are plain functions registered by
name; a leaf names its checker at creation, before any answer exists.
"""
from __future__ import annotations

import math


# -- known-answer checkers: fn(checker_args, answer_text) -> bool --------
def _extract_number(text: str) -> float | None:
    import re
    nums = re.findall(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    return float(nums[-1]) if nums else None


def check_sum_to_n(args: dict, answer: str) -> bool:
    n = int(args["n"])
    got = _extract_number(answer)
    return got is not None and got == n * (n + 1) // 2


def check_prime_product(args: dict, answer: str) -> bool:
    def first_primes(k: int) -> list[int]:
        primes, x = [], 2
        while len(primes) < k:
            if all(x % p for p in primes if p * p <= x):
                primes.append(x)
            x += 1
        return primes
    got = _extract_number(answer)
    want = math.prod(first_primes(int(args["k"])))
    return got is not None and got == want


def check_exact_value(args: dict, answer: str) -> bool:
    got = _extract_number(answer)
    return got is not None and abs(got - float(args["value"])) < 1e-9


CHECKERS = {
    "sum_to_n": check_sum_to_n,
    "prime_product": check_prime_product,
    "exact_value": check_exact_value,
}


class Worker:
    def __init__(self, name: str, backend):
        self.name = name
        self.backend = backend

    def work(self, board, leaf: dict) -> str:
        """Claim already made by the orchestrator. Returns an action tag."""
        reply = self.backend.complete(
            "You are a research worker. Answer the task with one final "
            "value or claim. If the task cannot be answered as stated, "
            "reply with exactly: SPLIT",
            f"Task: {leaf['task']}\nMOCK:{leaf['leaf_id']}")
        if reply.strip() == "SPLIT":
            board.stuck(leaf["leaf_id"], self.name,
                        "Worker backend reports the leaf cannot be answered "
                        "as stated; requesting a split into smaller leaves.")
            return "split"
        board.deliver(leaf["leaf_id"], self.name, reply.strip())
        return "delivered"


class Reviewer:
    def __init__(self, name: str):
        self.name = name

    def review(self, board, leaf: dict) -> str:
        """Close a delivered leaf. The reviewer never trusts the answer:
        it recomputes with the leaf's registered checker."""
        checker_name = leaf.get("checker")
        if not checker_name or checker_name not in CHECKERS:
            board.close(leaf["leaf_id"], self.name, "split",
                        "no registered checker: cannot be graded as stated, "
                        "split into checkable leaves")
            return "split"
        ok = CHECKERS[checker_name](leaf.get("checker_args", {}), leaf["answer"])
        if ok:
            board.close(leaf["leaf_id"], self.name, "proven",
                        f"checker {checker_name} recomputed and agrees")
            return "proven"
        board.close(leaf["leaf_id"], self.name, "refuted",
                    f"checker {checker_name} recomputed and disagrees")
        return "refuted"
