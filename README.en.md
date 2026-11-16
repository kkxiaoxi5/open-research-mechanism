# Open Research Mechanism

[简体中文](README.md) | **English** | [日本語](README.ja.md)

> Languages: docs, prompts, and the console UI are in English, with Japanese versions alongside (docs/ja/); Chinese is kept in the README only.

> An operating mechanism that lets multiple AI agents **collaboratively create new knowledge**.
> This repository publishes only the **mechanism**: how roles are divided, how tasks flow,
> how evidence is counted, and how the system scales without drifting.
> It contains no domain content (no data, strategies, or conclusions) — separating the
> mechanism from the content is the framework's first principle.

---

## What it solves

A single AI session doing research naturally slides into four failure modes
(this mechanism exists to block them):

1. **Task drift** — the work slowly bends away from the original question.
2. **Repeated work** — re-"verifying" things the agent already knows; never asking itself first whether it knows.
3. **Giving up / skipping verification** — abandoning a line when it gets hard; shipping after a quick look, then producing bugs.
4. **More agents, no more speed** — more hands only mean more commits; communication and review become the bottleneck and throughput falls.

## Core ideas

- **Use intelligence, not memory**: an agent's value is creating new tools, theories and explanations — not replaying conclusions from its training data.
- **Rules before action**: every claim gets a written prediction and decision criteria *before* the data is seen; no rules, no bet.
- **Mechanism before content**: fix how the work runs first, version it, accept it — then start the research itself.
- **Everything checkable**: tasks have claim records, deliveries have a fixed format, conclusions carry evidence levels, and failures are kept in full.

## Map of the mechanism

| Document | Contents |
|---|---|
| [docs/01-philosophy.md](docs/01-philosophy.md) | The four blocks: goals / tools / architecture / experience; the root requirements (three hard gates) |
| [docs/02-architecture.md](docs/02-architecture.md) | Roles and sessions: one session one name, a single receiving desk, authors never review their own work, two-line comparison |
| [docs/03-workflow.md](docs/03-workflow.md) | Task flow: proposition tree → small leaves → claim board → delivery blocks → review → acceptance; scheduled wake-ups and quota scheduling |
| [docs/04-evidence.md](docs/04-evidence.md) | Evidence discipline: prior predictions, a global trial count, an exposure registry, seen-direction marking, mutation testing, forward validation |
| [docs/05-uncertainty-and-tool-invention.md](docs/05-uncertainty-and-tool-invention.md) | Researching uncertainty: why classical probability is off-topic here; prove identifiability limits first, then invent new mathematical tools |
| [docs/06-mechanism-assurance.md](docs/06-mechanism-assurance.md) | How the mechanism guarantees itself: liveness (wake-ups, missed-delivery detection), correctness, recovery from six failure modes, anti-decay and degradation modes |
| [docs/07-tracker-and-snapshots.md](docs/07-tracker-and-snapshots.md) | Tickets and snapshots: human-scale work moves into a local tracker, and why its state must be exported back as snapshots; machine-scale vs human-scale layering; the single-point closing lesson |
| [docs/08-the-unquantifiable-layer.md](docs/08-the-unquantifiable-layer.md) | The unquantifiable layer: the jurisdiction of statistics; fair zones (a proved unknown is a design space, not a risk zone); the conversion loop and where acceleration belongs; a judgment credit ledger and defined-risk bets; pragmatic methods native to this market; the starvation law for layers without a dashboard |
| [docs/09-self-correction.md](docs/09-self-correction.md) | Self-correction: the rate equation (standard clarity × feedback frequency × cost of admitting × license to revise); six installable conditions — forced trace format, citable standard, external audit channel, an institutionalized daily trigger line, a license to iterate in steps, locatable errors; why fluent reflection is not a result |
| [docs/10-the-production-line.md](docs/10-the-production-line.md) | The production line: measure first (the bottleneck is queueing, not thinking); four stations — propose / rebuild / measure / apply; the ladder of stocked next levels; the data base pulled once; bottleneck accounting and the compute budget (on failure, move stations, do not add rules); essence-first questions as the ladder's quality gate; two blocks — preparation and the moment |
| [BOOTSTRAP.md](BOOTSTRAP.md) | **For agents:** a step-by-step protocol that reproduces this whole architecture from the documents alone — read order, runtime state, role instantiation, a known-answer demo, a self-verification battery, and an honest report of what no document can install. Machine-readable manifest: [architecture.json](architecture.json) |
| [templates/](templates/) | Ready-to-copy templates: claim card, delivery block, preregistration page, tool card, daily page |
| [reference/claimboard.py](reference/claimboard.py) | A minimal claim-board implementation (append-only log + three-outcome validation) |
| [agent/](agent/) | A runnable reference implementation of the whole mechanism (zero-dependency deep agent): decomposition into leaves, reviewer recomputation, three-outcome closing, tickets + snapshots, a read-only dashboard; pluggable model backends, demo runs with no API key |

## Clone and run the reference implementation

```bash
git clone https://github.com/kkxiaoxi5/open-research-mechanism.git
cd open-research-mechanism/agent
./deploy.sh            # Linux/macOS (Windows: .\deploy.ps1; server: docker compose up -d)
```

Open `http://127.0.0.1:8765` for the interactive console (decision queue /
claim board / tickets / members / activity). Zero dependencies, Python
≥ 3.11 only; the demo backend needs no key — see `agent/README.md` for
plugging in a real model.

## Quick start

1. Read `docs/01-philosophy.md` and write your own project's "root requirements" page.
2. Give every session a unique name and register the roster, per `docs/02-architecture.md`.
3. Dispatch the first card with `templates/claim-card.md`; require `templates/delivery-block.md` on delivery.
4. Keep review separate from authorship: nothing counts as "accepted" until a non-author reviews it.
5. One page per day: open by reconciling against the root requirements, then write which judgment changed today.

## What it is not

- Not a domain strategy library or dataset (keep content in your own private repository).
- Not a prompt collection: prompts are only one carrier of the mechanism; this repository publishes structure and rules.
- Not a fully automatic black box: key judgments (starting a line, upgrading evidence, using a result) keep explicit human decision points.

## License

MIT (see [LICENSE](LICENSE)).
