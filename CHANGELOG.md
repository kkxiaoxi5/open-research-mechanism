# Changelog

## 0.14.1 — 2026-11-15

- Chapter 09 gained a closing section, "What a Document Cannot
  Install" (English and Japanese): installing the chapter transfers
  the form, not three load-bearing ingredients — externality is a
  position, not a role-play an insider can simulate; the standard's
  authority lives in a live principal, not on the page; and the
  trace stock starts at zero, so a greenfield installation spends
  its first months accumulating stock rather than harvesting.
  Corollary: the mechanism minimizes dependence on the principal's
  live attention but cannot zero it; what cannot be documented is
  reserved for live things — a genuinely external auditor on a real
  cadence, and a principal who still occasionally asks.

## 0.14.0 — 2026-11-15

- New chapter `docs/09-self-correction.md` (with Japanese version in
  `docs/ja/`): the conditions that make a team revise itself.
  Contents: a rate equation for self-correction (standard clarity ×
  feedback frequency × inverse cost of admitting × license to
  revise); six installable conditions — a forced three-line trace
  format in every delivery block, a written citable standard, a
  standing external audit channel working from cited evidence, an
  institutionalized trigger (the daily line "what did I get wrong
  today, and who caught it"), a written license to iterate in
  steps, and locatable errors via explicit rule scopes; two
  cold-water clauses (a fluent reflection is not a result;
  self-reports are reconstructions, not introspection); and the
  mechanism's own failure modes (the "none" streak, audit decay,
  license rot). Docs-only release; the agent package is unchanged.

## 0.13.0 — 2026-11-15

- New chapter `docs/08-the-unquantifiable-layer.md` (with Japanese
  version in `docs/ja/`): which parts of a problem statistics has
  jurisdiction over, and what to do with the rest. Contents: the
  jurisdiction of statistics (rigor as a selection bias against the
  non-repeatable layer); fair zones — a proved symmetric unknown is
  a design space, not a risk zone, and impossibility results are
  booked as surveyed land; the conversion loop (intuition →
  structural proposition → scorable claim → verdict) and why
  acceleration belongs first to its front half; operating what
  stays unquantifiable (a judgment credit ledger, defined-risk
  bets, a two-sleeve funding rule); native pragmatic methods
  designed from the market's own anatomy, each shipping with its
  failure design, regime tags, and shelf life; and the starvation
  law — a work layer without a dashboard starves next to any layer
  with a closed loop. Docs-only release; the agent package is
  unchanged.

## 0.12.0 — 2026-11-15

- Console: light theme + operability pass (agent package 0.9.0).
  The dark terminal skin made controls hard to see and harder to
  click; the layout and supervision model stay, the chrome is now
  Anthropic's light palette (warm paper #faf9f5, white panels, clay
  orange accent) with real buttons everywhere — filled primary,
  outlined secondary, ≥26–32px targets, hover states, segmented
  tabs and language switch, focus rings on the composer. UI chrome
  type is sans; the transcript keeps monospace. Decision dialogs,
  expandable tool lines, persistent result lines, steering queue,
  and keyboard shortcuts all behave as in 0.11.0.

## 0.11.0 — 2026-11-15

- Console: from imitating Claude Code's *look* to imitating its
  *supervision model* (agent package 0.8.0). Pending decisions now
  interrupt the transcript as permission dialogs — full context
  (title, decider, next trigger, what approving/rejecting does),
  answerable by click or by keys 1 / 2. Tool-call lines expand on
  click (checker, arguments, claim→deliver→close chain); Ctrl+O
  toggles all. Round results and errors are persistent ✻ lines in
  the transcript instead of vanishing toasts. Messages sent while
  a round runs are marked as queued steering for the next round.
  The composer gains Claude-Code keyboard behaviour: ↑/↓ history,
  Shift+Tab cycles channels. The ⏵⏵ mode line is now honest: it
  shows the real wake mode (manual) and the channel agent's actual
  backend (model name or demo) instead of a decorative channel tag.

## 0.10.0 — 2026-11-15

- Console restyled as a pixel-level imitation of the Claude Code
  terminal UI (agent package 0.7.0): near-black background and
  monospace type throughout; welcome box with the orange ✻ spark;
  user messages on a highlighted bar with a `>` prompt; board events
  as `● Tool` lines with `⎿` result connectors; an animated ✻
  spinner with a rotating thinking verb while a round runs; a
  slash-command popup above the composer; the input box gains the
  `⏵⏵` mode line and `? for shortcuts`; the status line shows a
  block-character (█░) leaf-progress meter; cards and colored
  buttons removed in favour of plain terminal text, `❯` selection
  markers, and parenthesised status tags. All functions unchanged
  (agent management, per-agent model parameters, relation graph,
  persistent forkable chat, prompt navigator, EN/JA toggle).

## 0.9.0 — 2026-11-15

- Languages: everything except the READMEs is now English-first with
  Japanese alongside; Chinese is kept in the README only. Docs 01–07
  translated to English with Japanese versions in docs/ja/; templates
  likewise (templates/ja/); agent/PLAN.md + PLAN.ja.md; CONTRIBUTING
  (+ .ja); this changelog in English; claimboard.py comments and CLI
  help in English. Skills: SKILL.md is English-only, each skill gains
  a SKILL.ja.md, and the loader picks by MECH_AGENT_LANG (ja →
  SKILL.ja.md, fallback SKILL.md). Console UI is bilingual EN/JA
  (toggle in the status bar, default English, choice persisted);
  server-generated chat lines are English. Agent package 0.6.0.

## 0.8.0 — 2026-11-15

- Console restyled after Claude Code / Kilo Code (agent package 0.5.0): dark terminal
  aesthetics + monospace font; the central chat pane becomes a **transcript stream** instead of bubbles — user messages are
  `>` lines, member replies are `● name` blocks with the body hanging off a `⎿` connector line, and the claim board's
  open/claim/deliver/close events are interleaved into the all channel over time as **tool-call blocks**;
  the left sidebar becomes a compact row list (status dot + ID + one line of metadata);
  a new **status bar** at the bottom (leaf progress bar, ticket count, decision-queue reminder, current channel's
  model); the input box gains slash commands `/run` `/leaf` `/ticket` `/help`.
  Existing features unchanged: adding/removing members and per-member model parameters, relation graph, session persistence,
  prompt-navigation forking, decision queue.

## 0.7.2 — 2026-11-15

- Root fix for "deployed but nothing changed": the HTTP service turns off address reuse
  (`allow_reuse_address = False`). Previously on Windows a second instance could
  bind 8765 at the same time as the old service, and the browser hit them at random — kill one and another remained;
  now a second instance errors out and exits immediately, and together with deploy's port check,
  there is only ever one service on the port.

## 0.7.1 — 2026-11-15

- Foolproofing: the console subtitle shows the agent version (`/api/state` carries `version`),
  so you can tell at a glance whether you are looking at the new version; `deploy.sh` / `deploy.ps1` check port occupancy before starting —
  if the old service still holds 8765 they error clearly and say how to stop it, so "deployed but nothing changed" no longer happens
  (the new process cannot grab the port while the browser is still connected to the old service).

## 0.7.0 — 2026-11-15

- Console rebuilt per user feedback (agent package 0.4.0):
  - **Member management**: new `registry.py` member registry — add/remove agents in the UI,
    set model parameters per agent (model / base_url / temperature / enabled; API keys
    are stored only as environment-variable names); the coordinator rebuilds the work team from the registry every round (a new member starts work the next round).
  - **Relation graph**: a connection graph generated from real events (dispatch/deliver/close/chat/reply),
    with counts on the edges, instead of guessing who interacts with whom.
  - **Persistent sessions + modern layout**: left task-management sidebar (decision queue / claim board / tickets /
    members / relation graph), central chat pane split into per-member channels, sessions persisted in `chat.jsonl`;
    right-side **prompt navigation** lists all message nodes — click any node to
    jump to it and set it as a fork point, and the next message grows a new branch from there (parent pointer,
    original thread preserved). After a wake-up round, each member replies in its own channel from its real work record
    (with a real model connected, its model answers directly).
- Tests up to 10, all passing; deploy.sh verified live: a newly added member starts work in the same round, chat replies,
  and relation-graph edges are all correct.

## 0.6.2 — 2026-11-15

- Fixed failure to start on Windows: `board.py`'s file lock is now cross-platform (fcntl on POSIX,
  msvcrt on Windows); previously, cloning on Windows and running deploy.ps1 crashed directly on
  `import fcntl`. Added a regression test (block fcntl + stub msvcrt to verify
  the Windows branch imports and writes). `deploy.ps1` gains exit-code checks, so Python
  step failures no longer report false success. Agent package 0.3.1.

## 0.6.1 — 2026-11-15

- The trilingual main README and the agent README gain clone instructions (git clone + cd agent +
  deploy); the main README gains a "Clone and run the reference implementation" section.

## 0.6.0 — 2026-11-15

- The `agent/` interactive console ships (`webapp.py`, agent package 0.3.0): five views
  (decision queue / claim board / tickets / members / activity) + five actions (open a leaf, create a ticket,
  decide a ticket, message a member, wake a round). All writes are validated through the same Board/Tickets
  rule set, with no direct-write back door; user direct messages reach the corresponding worker via the inbox in the wake-up round.
  The `serve` command now goes through the console (new `--host`).
- One-click deployment: `deploy.sh` (Linux/macOS), `deploy.ps1` (Windows),
  `Dockerfile` + `docker-compose.yml` (server, state stored on a volume).
- Tests up to 8 (including the webapp's full HTTP flow), all passing; deploy.sh verified live:
  start → wake a round (3 proven / 1 refuted / 1 split) → open a leaf → shutdown, all working.

## 0.5.1 — 2026-11-15

- New bundled skill `tracker-workflow` (mapping between tickets/MRs/the claim board, tokens stored only on
  the server, MCP's applicable boundary, closing discipline); 7 skills in total, tests updated accordingly.
- `agent/PLAN.md` records two decisions: ② tickets use an external tracker (Gitea is fine,
  a TrackerAdapter interface, GitLab as the second adapter; the server side calls the REST API,
  MCP only for external conversational-shell agents); ④ the UI is required and must be interactive (writes validated through the server).

## 0.5.0 — 2026-11-15

- `agent/` bundles six required skills (`agent/skills/`, standard SKILL.md format):
  leaf-splitting, known-answer-tests,
  counterexample-hunting, proof-review,
  formalization, evidence-accounting.
  New `skills.py` loader (injects prompts by role) and a `skills` command;
  agent package version raised to 0.2.0; tests up to 5, all passing.

## 0.4.3 — 2026-11-15

- `agent/PLAN.md` records the user's decision: the primary scenario is **mathematical research** (open item ③ closed).
  The v0.2 demo set becomes a set of mathematical propositions; the checker ecosystem expands toward proof checking and symbolic recomputation;
  conversation forking is prioritized up, per-worker code workspaces are prioritized down.

## 0.4.2 — 2026-11-15

- New `agent/PLAN.md`: the v0.2–v0.5 plan (Swarm-style collaboration benchmarked against Antigravity /swarm,
  Claude Code-style conversation and task-branching UI, Docker server deployment; includes phased acceptance and
  the hard trade-off "conversations may branch, the ledger may not"). The three agent READMEs gain roadmap links.

## 0.4.1 — 2026-11-15

- Trilingual documents: the main README gains an English edition `README.en.md` and a Japanese edition `README.ja.md`;
  `agent/README` gains Simplified Chinese and Japanese editions; the four READMEs cross-link language switches at the top.
  (Trilingual editions of the docs/ body texts are future work.)

## 0.4.0 — 2026-11-15

- New `agent/`: a runnable reference implementation of the whole mechanism (deep-agent form, zero-dependency standard library):
  claim-board three-state closing, author/reviewer separation, coordinator wake-up loop, pluggable model backends
  (mock key-free demo + OpenAI-compatible interface), human-scale tickets with snapshot export,
  read-only visualization board; with demo problems (one run through proven/refuted/split) and unit tests.

## 0.3.0 — 2026-11-15

- New `docs/07-tracker-and-snapshots.md`: tickets and snapshots
  (why human-scale work moves into a locally deployed tracker; state returns to the repo as snapshots to preserve
  the boot-by-reading-files and backup disciplines; machine/human two layers kept separate; the failure lesson of single-point closing; pilot reconciliation).

## 0.2.0 — 2026-11-15

- New `docs/05-uncertainty-and-tool-invention.md`: methods for research uncertainty and the tool-invention pipeline
  (identifiability first, minimal synthetic worlds, formalization amplification, negative-result accounting).
- New `docs/06-mechanism-assurance.md`: the mechanism's self-assurance
  (liveness / correctness / six failure recoveries / anti-corrosion and degradation modes / weekly self-check table).

## 0.1.0 — 2026-11-15

- First public release: the mechanism layer extracted from a private research project's collaboration practice.
- README (Chinese and English), philosophy (four blocks + the fundamental requirements' three deadly gates), architecture (roles and information flow),
  workflow (proposition → leaf → claim board → delivery block → review → closing), evidence discipline (layering and five hard rules).
- Five templates: claim card, delivery block, preregistration page, tool card, daily page.
- Reference implementation: `reference/claimboard.py` (append-only log + three-valued outcome enforcement).
