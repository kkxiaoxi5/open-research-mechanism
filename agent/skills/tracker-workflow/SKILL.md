---
name: tracker-workflow
description: How tickets, merge requests and the claim board fit together on a local tracker (Gitea or GitLab). Use whenever work is filed, reviewed, or closed on the tracker.
roles: [coordinator, worker, reviewer]
---

# Tracker workflow

Tickets are the human-scale layer; leaves are the machine-scale layer.
The tracker (Gitea or GitLab, self-hosted) holds tickets and merge
requests; the board holds leaves. Neither replaces the other.

## The mapping

- **One leaf batch ↔ one ticket.** A ticket states the human-scale
  task; the leaves it decomposes into carry the ticket's number in
  their reference field. Closing the ticket requires every child leaf
  closed — the tracker workflow forbids closing a ticket whose
  children are open, and the snapshot shows violations.
- **A delivery that changes files arrives as a merge request.**
  The MR description *is* the delivery block (what changed, which
  numbers, how the checker ran). Review happens on the MR; the
  author never approves or merges their own MR — the tracker's
  approval rules enforce this, not politeness.
- **Questions and decisions are issues**, labeled `question` or
  `decision`, with the decider named in a field. They appear in the
  decision queue until closed with the decision text quoted verbatim.

## Connectivity rules

- Only the **server** holds the tracker API token. Workers and
  reviewers never call the tracker directly; they act through the
  server, which validates every write against the board's rules
  (three outcomes, no self-closing, required fields).
- MCP is **not** required for the system itself: the server uses the
  tracker's REST API. Add an MCP server only when an *external*
  chat-harness agent must operate the same tracker; the discipline
  in this skill is written to bind that case too.
- Every tracker write is mirrored into the snapshot export on the
  next cycle. If the tracker and the snapshot disagree, the snapshot
  is what sessions boot from, and the disagreement is a defect to
  report, not to silently paper over.

## Closing discipline

- Close reasons reuse the board's vocabulary where they apply
  (proven / refuted / split) plus `done` / `dropped` for plain tasks.
  A dropped ticket states why, in the ticket, forever.
- A ticket that has had no activity past its next-trigger date is
  escalated to the daily page automatically. Silence is a state the
  system surfaces, never a way for work to disappear.
