# mechanism-agent — the mechanism, as runnable code

The documents in this repository describe a mechanism for multi-agent
research that does not drift, stall, or fool itself. This folder is the
same mechanism as a small, dependency-free reference implementation
(Python ≥ 3.11, standard library only), so a single machine — including
an intranet machine — can run it end to end.

## What is inside

| Module | The mechanism piece it implements |
|---|---|
| `board.py` | Append-only claim board (JSONL + file lock). Leaves close only as **proven / refuted / split** — "cannot decide" is rejected at write time. Stuck requires a note and spawns a different-angle child. |
| `agents.py` | Worker (proposes) and reviewer (recomputes with a registered known-answer checker). The author can never close their own leaf — enforced, not conventional. |
| `orchestrator.py` | One wake-up cycle: reconcile expired leases and stuck leaves → dispatch → review → snapshot. |
| `backend.py` | Pluggable model backends: a deterministic mock (runs the demo with no keys) and an OpenAI-compatible client for a real model, public or intranet. |
| `tracker.py` | Human-scale tickets (tasks / questions / decisions, with a decision queue) and **snapshot export** back into files — tracker state never lives only inside a service. |
| `dashboard.py` | Read-only web dashboard: decision queue first, then the board, tickets, and closed-leaf evidence. It has no write path. |

## Run the demo (no keys, one minute)

```bash
cd agent
PYTHONPATH=src python -m mechanism_agent --home ./mech-state init
PYTHONPATH=src python -m mechanism_agent --home ./mech-state seed-demo
PYTHONPATH=src python -m mechanism_agent --home ./mech-state run
PYTHONPATH=src python -m mechanism_agent --home ./mech-state serve   # http://127.0.0.1:8765
```

The demo seeds three leaves so a single cycle exercises all three
outcomes: one answer is right (**proven**), one is wrong and the
reviewer's recomputation catches it (**refuted**), one cannot be
answered as stated (**split** into two checkable children, which then
close as proven).

Tests: `PYTHONPATH=src python -m unittest discover -s tests -v`

## Use a real model

Set `MECH_AGENT_BASE_URL`, `MECH_AGENT_API_KEY`, `MECH_AGENT_MODEL`
to any OpenAI-compatible endpoint (an intranet model server is fine)
and `run` uses it instead of the mock. Everything else — board,
tickets, snapshots, dashboard — is unchanged: **content and keys stay
on your machine; only the mechanism is shared.**

## Scope of v0.1

Deliberately minimal: single machine, no distributed workers, no
permission system (deploy behind your intranet's own controls).
What is not minimal is the part that matters: the closing rules,
the author/reviewer separation, and the snapshot contract are the
real ones from the framework documents, enforced by the code.
