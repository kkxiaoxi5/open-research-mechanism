# 01 · Philosophy: The Four Parts of the Framework and the Fundamental Requirements

This framework breaks "doing research in collaboration with AI" into four parts. Every review round reconciles against these four parts; every new arrangement first asks which part it belongs to and what it changes in that part.

## Goal

- First write down **what is truly wanted**, in the proposer's own original words, registered verbatim, append-only, never rewritten. An agent's derivations are not the proposer's views; quotations of the user's original words must carry their ID numbers, and relay chains are forbidden (relaying degrades content level by level).
- Goals have two tiers: the **main aim** (what is truly wanted) and the **floor** (a lower bound, not a ceiling). Parameters the proposer has not set — deadlines, success probabilities, and the like — are left blank: nobody may fill them in on their own and turn them into restrictions, nor use a self-invented deadline to veto a direction.
- A goal is a compass, not a daily exam question. Day to day, progress is measured by "verified progress + not dying," not by a binary check against the endpoint.

## Tools

- The core claim: let agents **use their intelligence to create new tools** — new mathematical tools, new theories, new interpretive frameworks — and then derive new methods from the new interpretations. What is already known does not need to be "discovered" again.
- Tools come in three classes, and the workload should keep a proportion (reference value: the creative class takes at least half):
  - **Class A · Representation & derivation**: new tools, new models, new interpretations (producing new knowledge).
  - **Class B · Judging & scoring**: scoring rules, benchmarks, evaluators (preventing self-deception).
  - **Class C · Stuck-point conversion**: turning "cannot proceed" into an explicit new problem (preventing stagnation).
- There is only one hard acceptance criterion for a tool: **it passes a known-answer test, and it has changed a judgment on a real problem.** A tool that is merely self-consistent inside a synthetic world and changes no judgment does not count.
- First-mover awareness: if everyone is doing something the same way, the advantage lies not in the method itself but in **using a new method at scale** — make "adding more agents speeds things up" a property of the architecture, not a slogan.

## Architecture

- The architecture must answer four things at once: **how people are divided, how information flows, how quality is assured, how scale grows**. Adding people without changing the architecture does not make output faster, only messier (see `02-architecture.md`).
- Two iron rules:
  - **Single intake**: all deliverables converge on one receiver who registers "received"; a message being "read" is not the same as a deliverable being "received."
  - **Authors never review their own work**: the person who made something does not judge it; reviewers recompute independently, without reading the author's conclusion first.
- The acceptance metric for scaling is real throughput: elapsed time from claim to independent acceptance, pure waiting time, rework rate, and **how many research judgments actually changed**. Agent counts, compute occupancy, and report page counts are not results.

## Experience / Evidence

- Distinguish two things that are often conflated:
  - **Contamination of inference**: data we have seen makes the effects we pick out look inflated — this is a self-deception problem, managed with preregistration, exposure registries, and a global trial count.
  - **Decay of effects**: whether an effect disappears because it becomes widely known — this is an empirical question, to be judged by crowding and cost; it cannot be deduced directly from the former.
- Rules like "an opened exam paper cannot be reused" must state clearly which of the two they guard against; a rule that cannot say will be circumvented and will not convince the people executing it. Legitimate ways to reuse must be given at the same time (for example, **blind replay**: masking subsequent results and isolating off-field information).
- A failed card is not garbage: by the standard of "an operator reviewing their own business," attribute each one item by item (measurement error / cost error / mechanism error / sample error), write down what could be changed, which decision the change would alter, and the conditions for reopening. Testing once and throwing away wastes costs already paid.

## Fundamental Requirements (Three Hard Gates)

Every project should have its own one-page "fundamental requirements," stored on its own page, visible to everyone, with changes leaving a trace. The reference version of this framework has three:

1. **Create something new**: every work round must be able to answer "what new tool / new interpretation / new judgment did this round create?"; a round that cannot answer is treated as drift — stop and realign first.
2. **Rules before action**: without a prediction and criteria written down beforehand, no conclusions may be drawn from results; even if something feels right it must be verified, and unverified claims may not be upgraded into conclusions.
3. **No giving up halfway**: a task has only three legal endings — proven, refuted, or split into smaller problems; "cannot determine" is not a legal ending, and being stuck must generate the next problem.

How to check (reference): the first section of the daily page carries a three-line summary table of the fundamental requirements; external cross-checking uses it as its first question; the weekly reconciliation checks this page first, then progress.
