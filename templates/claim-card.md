# Claim Card (used when dispatching a task)

```text
Card ID: <line>-<number> (e.g. A-012 / C-003)
Source: proposition ID / verbatim-quote ID / parent card ID
Task: one sentence stating exactly what is to be answered
Prior prediction: a prediction with an order of magnitude; state "if the result is X, which judgment changes"
Input version: version or commit hash of the data / spec (if unavailable, write "TBD" and explain)
Acceptance method: known-answer / bit-for-bit reproduction / machine-grading script (at least one; specify which)
Reviewer: a non-author, named
Compute and quota: expected usage; if a resource is shared with other lines, say so in the channel first
When stuck: write the blocker in three sentences + auto-generate a sub-task from a different angle (never wait idle)
```
