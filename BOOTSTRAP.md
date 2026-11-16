# BOOTSTRAP — Reproduce This Architecture

**You are an agent** (any harness: a coding agent, a chat agent with
file tools, this repository's own reference implementation). This
file is a protocol. Follow it in order and you will instantiate the
architecture this repository describes — not a summary of it, the
working system: a claim board with enforced rules, a ticket tracker
with a decision queue, role-bound skills, a production line of four
stations, and a daily page that reports itself.

Two modes:

- **Mode A — reference implementation.** Python ≥ 3.11, zero
  third-party dependencies. Use when you can run code.
- **Mode B — files only.** Any environment that can read and write
  files. You keep the same ledgers by hand, under the same rules.

Where the modes differ, both are given. Everything else is shared.

---

## Step 0 — Read, in this order

Do not skip. Each chapter installs one part of the machine; the
bootstrap steps after this one assume all of it.

| File | What it installs |
|---|---|
| `docs/01-philosophy.md` | The purpose and the four failure modes the mechanism exists to prevent |
| `docs/02-architecture.md` | Components and information flow |
| `docs/03-workflow.md` | The claim-board loop: split, claim, deliver, close |
| `docs/04-evidence.md` | Evidence accounting: pre-registration, minimum detectable effect, the global trial count |
| `docs/05-uncertainty-and-tool-invention.md` | Jurisdiction of tests; inventing tools vs applying them |
| `docs/06-mechanism-assurance.md` | Known-answer tests, mutation checks, blind judging |
| `docs/07-tracker-and-snapshots.md` | Human-scale work in a tracker; state exported back as snapshots |
| `docs/08-the-unquantifiable-layer.md` | Fair zones, the conversion loop, bets with pre-written maximum loss |
| `docs/09-self-correction.md` | The conditions that make a team revise itself — read its closing section before you promise anything |
| `docs/10-the-production-line.md` | The four stations, the ladder, bottleneck accounting, essence-first questions |
| `architecture.json` | The machine-readable manifest of components and invariants |

## Step 1 — Create the runtime state

Mode A:

```bash
cd agent
pip install -e .            # provides the `mechanism-agent` command
                            # (or: PYTHONPATH=src python -m mechanism_agent)
mechanism-agent --home ./mech-state init
```

This creates, under the home directory:

- `board.jsonl` — the claim board (append-only);
- `tickets.json` — the tracker state;
- `snapshot/` — exported state snapshots.

Mode B: create the same three artifacts yourself. `board.jsonl` is
one JSON object per line, appended, never edited or deleted.
`reference/claimboard.py` is a dependency-free implementation of
the board rules you can copy or mirror.

## Step 2 — Instantiate the roles

Create one agent (or one clearly separated session) per role. Write
each role card into your workspace before any work starts. The
roles, from chapters 03 and 10:

| Role | Duty | Hard prohibitions |
|---|---|---|
| **Proposer** | Stocks the ladder: levels with claim, assumptions, judging method, data needs | May not judge own levels |
| **Rebuilder** | Independently re-derives each level from its statement before it is booked | May not book a level they proposed |
| **Opponent** | Tries to break each level (counterexamples, mutation, scope attacks) | — |
| **Measurer** | Owns the data base inventory and the measurement cards | May not re-litigate data access per card |
| **Applier** | Converts verified levels into preparation cards (advance / in-the-moment), hung as paper bets | May not score own cards |
| **Reviewer** | Closes leaves and scores cards, from recomputation | May not close a leaf they authored |
| **Lead** | Owns the task table, the daily page, and the self-correction line | May not be the only release authority — tier it |
| **External auditor** | Audits the team against the written standard, from cited evidence, on a fixed cadence | Must be genuinely external (chapter 09: a seat can be reserved by a document; it cannot be sat in by one) |

Board rules that bind every role, in both modes:

- outcomes are exactly `proven` / `refuted` / `split` — "cannot
  tell" is not an outcome; a stuck leaf requires a three-sentence
  note and spawns a different-angle child;
- a leaf's author cannot close it;
- a bet card is immutable after registration — void and re-open,
  never edit;
- the author of a card never scores it.

## Step 3 — Load the skills by role

Mode A: `mechanism-agent skills` lists the bundled skills and the
roles each serves; the loader injects the skills matching an
agent's role into that agent's prompt (`MECH_AGENT_LANG=ja` selects
the Japanese texts). Mode B: read `agent/skills/<name>/SKILL.md`
for each skill whose front-matter `roles` include your role, and
treat the text as your operating playbook.

## Step 4 — Run the known-answer demo

Mode A:

```bash
mechanism-agent --home ./mech-state seed-demo
mechanism-agent --home ./mech-state run
```

Expected result — this is a known-answer test of the whole loop,
and it must come out exactly like this:

- **D1** (sum of 1..100) → **proven**;
- **D2** (product of the first five primes; the demo backend
  deliberately answers wrong) → **refuted**;
- **D3** (a question that cannot be answered as posed) →
  **split**, then its child leaves → **proven**.

Any other result means the installation is wrong. Do not proceed
to real work on a loop that fails its own demo. Mode B: reproduce
the same three leaves by hand on your board, with a second role
closing them, and require the same outcomes.

## Step 5 — Self-verification battery

All of these must pass; report each result, do not summarize them
away.

Mode A:

```bash
cd agent && PYTHONPATH=src python -m unittest discover -s tests
```

All tests green. Then check the invariants against your live
state:

1. `board.jsonl` parses as one JSON object per line, append-only
   (no line differs from the previous snapshot).
2. Every closed leaf's outcome is one of `proven` / `refuted` /
   `split`.
3. No closed leaf was closed by its author (attempt one: the board
   must refuse).
4. `mechanism-agent --home ./mech-state snapshot` exports a
   snapshot without error.
5. Each role from Step 2 exists as a written card, and each has
   its skills loaded (Step 3).
6. The ladder exists as a written queue with at least the floor
   depth your team set (chapter 10 suggests a handful), every level
   carrying claim / assumptions / judging method / data needs.

## Step 6 — First operating cycle

1. State the team's **essence questions** (chapter 10) in writing,
   before opening any level that hangs from data alone.
2. Stock the ladder; prove the data-free levels first.
3. Build the data base inventory once (chapter 10): series,
   coverage, known biases, unavailable-for-free list with bias
   annotations; the default on paying is *do not buy*, surfaced to
   the principal on a fixed cadence.
4. Open the daily page with, at minimum: the conversion-loop
   counts, the innovation count and the fair-zone count, the
   usage/budget state, and the self-correction line — *"what did
   the lead get wrong today, and who caught it"* (write "none" if
   none; a long "none" streak is a signal, not a trophy).
5. Set the first reconciliation date now, and write down what will
   be counted there.

## Step 7 — Report back to the principal

Report, in this order: what was instantiated (roles, state,
skills); the Step 4 demo outcomes, verbatim; the Step 5 battery,
item by item; and what this document did **not** install. Chapter
09's closing section names three things no document can install —
a genuinely external auditor, a standard whose authority lives in
a live principal, and a trace stock, which starts at zero. Say so
plainly. A bootstrap that claims completeness is the first failure
mode.
