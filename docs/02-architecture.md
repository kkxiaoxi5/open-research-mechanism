# 02 · Architecture: Roles, Sessions, and Information Flow

## One Session, One Name

- Each long-lived session = one post = one unique name. The name is the addressee: assignments, messages, and deliveries all name names.
- Shared names fight over inboxes, cursors, and duplicate replies — this is a measured failure mode, not fussiness.
- Before a new session starts work, register one line in the roster: name / runtime environment / role / what to ask it for / status.
- Temporary sub-agents are not posts: they sign with their origin (e.g. `main session · sub-agent`), stay out of the roster, and take no assignments.

## Role Reference Table

| Role | Responsibilities | Does not do |
|---|---|---|
| Lead (intake) | Assigns work, registers receipt, maintains the single task-status table, schedules resources (quota / compute) | Does not double as leader of a specific research line; does not approve every step of exploration |
| Research lead (one per line) | The line's problem specifications, prior predictions, closing pages | Does not review their own output |
| Executor / solver | Runs computations, replays, counts, finds data, per specification | Does not change the specification; reports specification problems instead of quietly changing the caliber |
| Tool maintenance | Builds and maintains shared tools (checkers, ledgers, scheduling) | Does not use unreviewed tools as judges |
| Reviewers (at least two, mutually independent) | Blind read-back against the question, code audit, independent recomputation, mutation tests | Does not judge after reading the author's conclusion first; does not take rework on work they reviewed |
| Data / channel maintenance | Data landing, integrity gates, exposure registry | Does not touch research judgments |
| Coordinator | Registers the user's original words, progress pages, external reporting | Does not assign research work |
| External review (optional) | Read-only review, proposes candidate improvements | Does not assign work or modify files; its output is always labeled "candidate, not accepted" |

## Single Intake

- The whole project has exactly one task-status table and exactly one writer (the lead).
- Delivery flow: the deliverable opens with a delivery block → notify the intake over the message channel → the intake verifies and registers it in the status table.
- "Read" ≠ "received"; "received" ≠ "conclusion is positive." The three states are recorded separately.
- The intake is a convergence point, not an approval point: trial and error at the exploration level needs no step-by-step approval; only three kinds of action pass a gate — **claiming a discovery, upgrading evidence, consuming resources**.

## Two-Line Cross-Check (Optional, Strongly Recommended)

- Same repository, same ledger, two autonomous research lines (Line A / Line B) with equal exploration rights.
- Comparing the two lines requires **same problem, same resource constraints, same acceptance standards**; comparing strength with one line fixing old problems and the other doing new problems is invalid.
- Cross-line checking is a feature, not an incident: one line runs mutation tests on the other's tools and hunts for exposure-registry errors; it counts only after a third party independently reproduces it.
- When both lines access the same batch of data, their query and selection histories are **counted together**; keeping separate books is not allowed.

## Information Flow

- **Source of truth for the user's original words**: exactly one registry for the proposer's original words, append-only, with ID numbers; other documents cite the numbers and do not copy paraphrases.
- **Source of truth for task status**: the status table only; progress claims in chat do not count, and on mismatch the table prevails and the discrepancy is traced back.
- **Message channel**: daily communication goes through lightweight messages / a bridge; only exceptions (safety, decisions, disputes) are escalated to formal records.
- **Daily page**: one page per line per day; the first section reconciles against the fundamental requirements, and the body writes only "which judgment changed today, where it is stuck, what is next."
- **Push discipline**: at the end of each round, push results to the remote backup; a mismatch between local HEAD and the remote counts as backup incomplete. (Without this, outside observers forever see yesterday's world.)

## Quota and Scheduling

- Model quota, compute, and reviewer labor are all **schedulable resources**, written into the status table and arranged centrally: when one kind of quota is frozen, route work to roles that do not depend on it instead of halting the whole line.
- The lead may run on **timed wake-ups**: each wake-up first runs a read-only checker (any missed deliveries? any timed-out claims?), then reads the inbox, verifies commits, and updates the status table. Without an automatic driver, a stopped session stays stopped — so the checker must show at a glance "who is stuck, and for how long."
