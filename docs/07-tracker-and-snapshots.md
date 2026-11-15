# 07 · Tickets and Snapshots: Human-Scale Work Goes into a Tracker, State Returns to the Repository as Snapshots

Once multi-session collaboration is running, **human-scale** work — tasks, questions, decisions, on the order of dozens of items — quickly crushes markdown tables: state is copied by hand, closing depends on someone remembering, and "what is waiting on whom" requires reading the whole text to know. This chapter's solution: **move this kind of work into a locally deployed open-source issue tracker; the tracker's state is periodically exported as snapshot files back into the repository.** Machine-scale work (batch-generated micro-tasks) does not go into the tracker; it stays in the appendix-style append-only ledger (see the claim board in `03-workflow.md`).

## Why Use a Ready-Made Tracker Instead of Hand-Rolling Tables

- Tables have no field constraints: owner, deadline, and next trigger can be saved with whole columns empty — that is exactly how misses and forgettings happen. A tracker's required fields and state machine intercept **at write time**.
- Tables have no notifications: a state change depends on someone happening to read it. A tracker's assignments, watches, and due reminders turn "missed receipt" from a matter of luck into a property of the system.
- Tables have no queries: "unanswered questions," "items awaiting someone's decision," "overdue work" should be saved queries that produce a table in one click, not something a person re-derives by reading everything each time.
- A hand-rolled table is, in essence, a low-quality rewrite of a tracker — which has spent twenty years solving exactly these three things: misses, forgettings, and no history.

## Why Snapshots Are Mandatory (The Key Point of This Chapter)

A tracker has a real cost: **state leaves the repository**. For a system built on "sessions boot by reading files and back up via commit history," this bites:

- A new session cannot read the latest state at boot and falls back to relayed paraphrase;
- Repository backups (remote HEAD verification) do not cover the state inside the tracker;
- If the tracker ever stops or is abandoned, its historical state is lost wholesale.

The answer is not to reject the tracker but to give it a return pipe:

- Operate the tracker through an **API client that connects only locally** (open tickets, comment, close tickets, export); the client itself lives in the repository and is tested;
- Periodically **export the tracker's full state as snapshot files and commit them back into the repository** (e.g. JSON/CSV plus a human-readable summary); the snapshot is both the backup and the boot reading: sessions read the snapshot at boot, and deep operations go through the API;
- Prefer tracker options that are **single-file / lightweight local deployments** (such as Gitea-class open-source tools that combine code hosting and tickets; when deeper workflow is required, Redmine-class tools), so the whole setup can be rebuilt on one machine.

## Layering: What Goes into the Tracker, What Does Not

| Layer | Scale | Carrier |
|---|---|---|
| Machine scale: batch micro-tasks, automatic scoring, parent–child derivation | hundreds–thousands | Append-only ledger (claim board), managed by programs |
| Human scale: tasks, questions, decisions, incidents | tens–hundreds | Tracker, managed by fields and workflow |
| Immutable sources of truth: original instructions, documents, evidence | — | The git repository; tickets carry only ID numbers and links |

Stuffing machine scale into a tracker crushes the tracker first (noise, batch operations, and custom state machines are not what it was designed for); leaving human scale in tables leaves misses and forgettings unsolvable. Layering avoids both directions of failure.

## A Lesson That Must Be Written into the Workflow: Single-Point Closing

The most common way a tracker deployment fails is not that nobody opens tickets, but that **the right to close tickets is concentrated in one person**: once that person stalls, unclosed tickets pile up and the whole system is abandoned. So the workflow needs at least two rules:

- Closing rights are not single-point (reviewers and the coordinator can both close; authors still may not close their own);
- Tickets untouched past a timeout are automatically escalated into the daily page / daily report, instead of lying there quietly.

## Pilot Discipline

Deployment is not adoption. Agree on a near-term **reconciliation day**: check ticket by ticket whether the tracker matches the actual work, whether the daily page has begun to be generated from queries / snapshots, and whether closing is still single-point. If the reconciliation fails, fix it or roll back to tables, and write the reason into the change log — tools, like conclusions, must withstand being said no to after use.
