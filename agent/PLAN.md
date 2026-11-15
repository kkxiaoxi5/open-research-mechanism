# Plan: mechanism-agent v0.2–v0.5
## Swarm-style collaboration + conversational task-branching UI + Docker server deployment

- Status: plan (not started). Baseline: `agent/` v0.1 (released, commit 79c3e100).
- Benchmarks: Google Antigravity's `/swarm` (named agent teams + shared message board + verifiers),
  and Claude Code-style conversation (one conversation thread per member, forkable, rewindable to checkpoints).
- Constraints unchanged: mechanism separated from content; all of v0.1's enforced rules —
  three-state closing, authors do not review their own work, snapshots back into the repo —
  are retained in full. New features may only grow on top of them, never bypass them.

---

## 1. Conclusion first (feasibility)

**Feasible.** The v0.1 core (claim board = public ledger, coordinator, work/review separation, snapshots)
is exactly the skeleton of a Swarm: Antigravity's coordinator splitting tasks, named workers,
public briefs, shared board, and verifier review correspond one-to-one with this mechanism's
leaf-splitting, claiming, delivery blocks, and review-based closing. What is mainly missing is three
layers: an **event/mention layer** (the board upgraded from a state log to a message bus),
**member lifecycle** (sleep/wake/pause/exit), and **server and UI** (real-time push, conversation
trees and forking). Only two places are genuinely hard: making the storage interface safe for
concurrent writes, and the data model for forking — Section 5 gives the trade-off:
**conversations may branch; the ledger may not.**

## 2. Benchmark feature list (item-by-item mapping)

| Antigravity /swarm | Corresponding implementation in this plan | Phase |
|---|---|---|
| The current conversation becomes the coordinator, splitting work into non-colliding chunks | When the coordinator splits a proposition into leaves, it attaches a "mutual-exclusion statement" (the leaves' change surfaces do not overlap; overlaps must be explicitly registered) | v0.2 |
| Named workers (@parser) and numbered groups (@fix-1..4) | Extended member roster: the name is the post; leaves of the same kind automatically open numbered groups | v0.2 |
| One public brief per person (what they own / what they must not touch / completion criteria) | Claim cards posted publicly on the board; fields = the three columns of the claim-card template, visible to everyone | v0.2 |
| Verifiers: 1 per 2–4 workers, read diffs, run tests, send work back to the author for fixes | Reviewer ratio is configurable; review may use a **different backend/model** (cross-model review); a new "rework round": a refutation is not immediately final — the author may fix for one round and be re-reviewed; rounds are capped and accounted | v0.2 |
| Shared board, @name/@group/@all mentions; no private chat, everything public and ordered | The board gains a post event stream (mentions, questions, delivery summaries, review conclusions are all one kind of post); no private-message channel between members | v0.2 |
| Idle members sleep without consuming tokens, woken only when mentioned | Member state machine gains `waiting`: event-driven wake-up (mentioned / assigned a leaf / lease expiry), replacing pure timed polling; timed wake-ups remain as a fallback reconciliation | v0.2 |
| @monitor: speaks only when everyone is silent and work is unfinished, calling whoever can move it forward | A monitor role: silence detection = a formalization of the existing missed-message/stall checks, with thresholds; reports facts only, dispatches nothing | v0.2 |
| Member states Active / Waiting / Killed; quota exhausted → paused (reported once, no retry storm), resumed only by a new post / model switch / user message | The state machine implements exactly this; a quota error from the backend → member `paused` + a single notice left on the board; the three resume triggers are fixed in writing | v0.2 |
| A worker can switch models mid-task without losing the conversation | A member's backend is a replaceable field; switching models changes only the field — conversation and claims are unchanged | v0.2 |
| Shared workspace by default; on edit collision, one working copy per person, landed before exit | One git worktree per worker; before a leaf closes, changes must be landed as a delivery block; on exit, its worktree is deleted | v0.5 |
| Swarm panel: Board (real-time stream, New divider, search/filter, Follow) / Members (Active/standby/exited, click to enter their conversation) / Graph (mention graph, weights, replay) | The web UI implements the three views accordingly (Section 4); Graph replay = re-enacting by board event sequence number | v0.3–0.4 |
| Direct messages to a single worker (not via the board) | Exception channel: user → single member direct messages (Q&A, approving tool calls), kept on record but not entering the public stream; members still may not message each other privately | v0.3 |

## 3. UI: Claude Code-style conversation and task branching

- **One conversation thread per member**: all of a member's exchanges (brief, questions, deliveries, review comments)
  form one readable conversation, read top to bottom like a Claude Code session, rather than scattered across logs.
- **The task tree is a branch tree**: splitting a leaf smaller (a split closing) is naturally a branch — the parent leaf closes,
  each child leaf opens its own conversation thread; the UI presents "who branched from whom" as a tree/graph.
- **Forking**: the user or the coordinator may fork at any message in any conversation:
  the new conversation starts from that prefix and continues with a different approach (e.g. redo with a different model, re-ask from a different angle).
  A fork is a new thread; the old thread is preserved as-is — **history may not be rewritten**, consistent with the append-only ledger.
- **Checkpoints and rewind**: each delivery/closing forms a checkpoint on the conversation;
  rewinding = forking a new thread from a checkpoint, not turning time back and deleting records.
- **Where the human sits**: the UI's first screen is still the "awaiting decision" queue (settled by the v0.1 board);
  conversations and branches are the second layer, entered by clicking any member / any leaf.

## 4. Server architecture (Docker deployment)

One server machine; docker compose brings up the whole stack; intranet deployment depends on no external service
(model endpoints excepted, and those may point at intranet models).

```yaml
services:
  server:      # API + coordinator: sole writer of the board/tickets, SSE push of the real-time stream
  worker:      # stateless work/review agent processes, scalable to multiple replicas; only claim, never write the store directly
  web:         # UI static assets + reverse proxy (Board/Members/Graph/conversation tree)
  db:          # Postgres: board events, conversations, tickets (see Section 5, storage layering)
  gitea:       # optional: human-scale tickets and code hosting (the shape of docs/07), or use built-in tickets
volumes:
  state:       # snapshots and exports; snapshots are committed back to the git repo on a schedule (backup discipline unchanged)
```

- **One language throughout**: the server stays in Python (standard library → a light framework, FastAPI),
  the UI is a no-build-step frontend (vanilla JS + SSE), avoiding a build chain in intranet deployment.
- **Real-time**: server → browser uses SSE (one-way push is enough: board stream, member states);
  browser → server operations (dispatching work, direct messages, approvals) use ordinary POSTs.
- **Sole writer**: all writes pass through the server's API validation (v0.1's board rules moved to the server unchanged:
  three-state closing, authors cannot close their own work, required fields intercepted server-side),
  worker processes have no direct-write permission — an M1157-style "crashing the board by writing" becomes architecturally impossible.

## 5. Data model and two hard trade-offs

1. **Conversations may branch; the ledger may not.** The board's event stream is the whole team's single sequence of facts;
   forking happens only at the conversation and workspace level: a forked thread reads the same ledger,
   and deliveries still go through the same review path. If the ledger were allowed to fork, the two lines would each grow
   their own "verified conclusions" and the evidence system would fail on the spot — this is the most important difference
   between this plan and general multi-agent frameworks. Fixed in writing, not up for discussion.
2. **Storage layering**: v0.1's JSONL is retained as the **export/snapshot format** (audit and backup);
   the server's runtime state goes into Postgres (concurrency and queries need it). The two are joined by one-way export
   from the server: the database is the runtime source of truth, snapshots are backups and boot-time reading —
   the same discipline as docs/07's "tickets + snapshots", extended to all state.

## 6. Phases and acceptance

| Phase | Content | Acceptance (decidable) |
|---|---|---|
| v0.2 | Swarm runtime: post/mention layer, member state machine with sleep/wake, monitor, rework rounds, cross-model review, quota-pause semantics | Math-research demo set: one small proposition set divided among 4 workers (proof attempts / counterexample hunting / lemma splitting) + 1 cross-model verifier re-checking, run end to end; deliberately make one worker hit a quota error — the board shows exactly one notice and no retries; when all members are silent, the monitor speaks within its threshold |
| v0.3 | Server + Docker: compose brings up server/worker/web/db; SSE real-time Board and Members views; user direct messages | On a clean machine, after `docker compose up`, in the browser you can view the board, dispatch work, and reach a specific worker directly; killing a worker container loses no state |
| v0.4 | Conversation tree and branching: per-member conversation threads, split-branch visualization, fork from any message, checkpoint rewind, Graph mention graph + replay | Fork a new thread from the middle of a conversation and run it to closing; the old thread and the ledger are unaffected; replay can re-enact the whole course by event sequence number |
| v0.5 | Workspace isolation and hardening: per-worker worktrees, landing checks, exit cleanup; per-post quota accounting panel | Two workers editing the same file do not overwrite each other; an exited worker's worktree is cleaned and its changes are either landed or discarded (on record) |

Each phase follows the old rule: register the acceptance criteria in this plan first, then start work; a phase that fails acceptance does not proceed to the next.

> Progress note (2026-11-15): the interactive console has already landed ahead of schedule in local form (`webapp.py`:
> five views — decision queue / claim board / tickets / members / activity — plus open a leaf, decide, direct message, wake a round,
> with writes validated through Board/Tickets), and the one-click deployment trio (deploy.sh / deploy.ps1 /
> docker-compose) is attached — of the v0.3 acceptance, "in the browser you can view the board, dispatch work, and reach directly"
> is already achieved in single-machine form; the remaining increment is multi-process serverization (server/worker split,
> Postgres runtime state) and SSE real-time push.

## 7. Risks and open items

- **Concurrency correctness**: races when multiple workers claim/close at once are solved by serialized writes at the server
  + leases (v0.1 already has lease semantics); v0.2 produces a concurrency stress test before scaling up.
- **Context cost**: a Swarm-style public board makes every member read the whole board — a large board must have
  filtered views (read only what concerns you), or token cost grows quadratically with headcount. Antigravity
  presses this down with "sleep + mention wake-up"; this plan does the same and adds "members subscribe by default only to posts that mention them".
- **Awaiting user decision**: the strength of UI login/permissions (a minimal intranet deployment may rely on network isolation first,
  but the UI itself must be interactive — see decided item ④).
- **Decided (2026-11-15, user)**: ② tickets use an **external tracker (Gitea is fine)**.
  Architecturally this is a TrackerAdapter interface: Gitea is the first adapter; where a company already runs a local
  GitLab, a GitLab adapter is used (same interface, issues/MR/CI in one, MR approval natively corresponding to "authors do not review their own work"). The connection method is settled: **the server calls the REST API**
  (the token lives only on the server; agents do not connect directly); **MCP is not needed** — it is added only when an external
  conversational-shell agent (such as a Claude Code-class tool) needs to operate the same tracker;
  **a skill is needed**: ticket/MR/closing discipline is bundled as `tracker-workflow`.
  ④ **The UI is a necessity and must be interactive** (the user wants to interact with the system): dispatching work, direct messages,
  approvals, and forks all originate from the UI, but all are written through the server's API validation —
  the v0.1 board's "read-only" was only a demo form; from v0.3 the UI is the official operating surface,
  and the sole writer is still the server.
- **Decided (2026-11-15, user)**: ③ the primary scenario is set to **mathematical research**. The demo problems and the checker
  ecosystem are calibrated to research problems: proposition posing, proof attempts, counterexample hunting, symbolic/numeric
  recomputation of known answers; the checker registry expands toward proof checking (formal-verification interfaces) and symbolic computation.
  Code problems are demoted to a secondary scenario; accordingly, v0.5's per-worker code workspaces (worktrees)
  are deprioritized, and conversation forking (different paths through a proof attempt) is prioritized — in mathematics,
  "try a different approach" is the primary need; "many people editing the same file" is not.

## 8. Relation to existing documents

This plan changes none of the rules in docs/01–07; it implements docs/02 (architecture) scaled up
into server form. As each phase lands, the CHANGELOG records a version;
if a phase's acceptance is rejected, this plan is revised in place with the old version's record kept — the plan itself also follows
this framework's evidence discipline.
