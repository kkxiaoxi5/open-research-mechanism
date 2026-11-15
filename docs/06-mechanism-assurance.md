# 06 · Self-Assurance of the Mechanism: Not Stalling Midway, Not Quietly Degrading

The greatest risk to a mechanism is not being opposed, but **grinding to a halt as it runs, or quietly changing flavor**, with nobody noticing. This chapter describes how a mechanism assures itself: liveness, correctness, recovery, and anti-decay.

## Liveness: If It Stops, Somebody Must Know

- **Timed wake-ups**: the coordinator is woken on a fixed rhythm (rather than "looks in when free"); each wake-up first runs a read-only checker, then handles business. The checker answers only three questions: whose delivery was missed, whose claim has timed out, which table is stale.
- **Heartbeat and single writer**: every class of continuous process (data landing, bookkeeping, monitoring) has a single writer, and writes carry timestamps; no new timestamp beyond the agreed interval = the process is dead — handled as an incident, not as "no data today."
- **Missed-delivery detection**: between a message being "read" and a deliverable being "received" there is an independent reconciliation (the checker cross-verifies the status table against the commit history); a missed delivery is necessarily picked up at the next wake-up.

## Correctness: If It Is Wrong, It Must Be Catchable

- **Single source of truth + lock**: the user's original words, the task status, and the evidence ledger each have exactly one source of truth; writes go through a unified entry point under a lock, and editing files directly around the entry point is forbidden.
- **Mutation tests apply to the mechanism itself**: periodically mutate key rules — deliberately write one place wrong (omit a required field, change a threshold) and see whether the gate catches it; a gate that cannot catch is counted as nonexistent.
- **Gates up front**: automatic validation before submission (required fields, the prior-power file exists, caliber labels present); nonconforming items are returned on the spot rather than fished out by later review.
- **Authors never review their own work** also applies to mechanism changes: whoever changes a rule cannot alone declare the new rule in effect; rule changes leave a trace (who, when, on the basis of which original words / resolution), and a rule with no provenance does not take effect.

## Recovery: If It Breaks, Work Must Be Continuable

Delivery and handover are designed to be **idempotent**; each of six failure modes needs a re-runnable test:

1. The same delivery is delivered twice → not booked twice.
2. A new reply arrives at the instant of reading → not lost, not read out of alignment.
3. Several people are notified, one closes the item → the others' to-dos correctly lapse.
4. After "received," the executor stalls → the checker raises a timeout alarm and the item can be reassigned.
5. An old instance delivers late → judged by version; it does not overwrite the new version's conclusion.
6. A v1 delivery arrives after the v2 delivery → the status table follows the version and does not roll back.

- **Handover drill**: a new session, relying only on the handover page and the source-of-truth files, should be able to reproduce the key numbers and pick up the work; if the drill fails, knowledge is still locked inside some session, and that is treated as an architecture defect.
- **Backup acceptance**: backup counts as complete only when local and remote HEADs are verified to match, one by one; "copied to another disk" is not a backup.

## Anti-Decay: Not Changing Flavor over Time

- **Periodic reconciliation against the fundamental requirements**: the daily page reconciles first, the week reconciles fully; reconciliation verdicts are only "conforming / drifting (pointing at which item)," and drift items enter the next round's claim board.
- **Degraded modes written down**: when resources (quota, compute, reviewer labor) freeze, the mechanism does not stall but degrades along pre-set routes — which work continues, which pauses, who may not be woken during the freeze — all written into the status table in advance; when the freeze lifts, re-read the status before assigning work.
- **Citation hygiene**: periodically sample in-use conclusions for evidence-tier and caliber labels; sentence patterns like "not answered" written as "excluded" are registered as incidents, and every citing place is corrected.
- **The mechanism's own version**: this framework's documents carry version numbers and a change log; any "we have always done it this way" that cannot be found in the documents counts as nonexistent.

## A Self-Check Table (Run Weekly)

| Question | Evidence |
|---|---|
| Last week, was any delivery missed for more than one wake-up round? | Checker logs |
| Is every continuous process's heartbeat within its interval? | Timestamp sampling |
| Are the tests for all six recovery failure modes still green? | Test output |
| Among last week's closings, was there any "cannot determine" or empty waiting? | Claim board scan |
| Was the fundamental-requirements reconciliation done? Did drift items enter the board? | Daily pages + status table |
| Do local and remote HEADs match? | Per-repository verification record |
