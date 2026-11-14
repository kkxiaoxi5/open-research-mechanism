---
name: evidence-accounting
description: Keep the trial count, exposure registry and seen-direction marks honest. Use whenever data is read, a hypothesis is tested, or a result is cited.
roles: [coordinator, worker, reviewer]
---

# Evidence accounting（证据记账）

Selection is invisible unless it is written down. This skill is the
writing-down: every look at data, every test, every citation leaves a
line in a ledger, so that later claims can be priced honestly.

## The three ledgers

1. **Global trial count (N)**: every test of a hypothesis against data
   increments one project-wide counter — including tests that "were
   just a quick look" and tests run by other lines on shared data.
   N never resets, not for a new session, a new repo, or a new year.
2. **Exposure registry**: for each dataset/segment, record who read
   what, in which direction, and when. A segment that has been read
   for direction is marked seen; conclusions from it are labeled with
   that mark wherever they are cited.
3. **Seen-direction and reuse pricing**: reusing an already-opened
   segment is allowed and priced (e.g. a queue fee that raises the
   bar with each reuse of *that segment*); what is forbidden is
   presenting a reuse as a first look.

## Operating rules

- Register **before** reading direction, not after. A registration
  written after the result is known is marked late, and late marks
  downgrade the evidence level of everything downstream.
- A citation must carry its evidence level (exploratory / reviewed /
  independently confirmed / forward) and its exposure marks. A number
  quoted without them is treated as unverified, however often it has
  been repeated.
- Failed and abandoned tests stay in the ledger with their outcomes.
  Deleting a failure is the one unforgivable edit: it falsifies every
  rate computed from the ledger afterwards.
- When a number is corrected, the correction propagates: every page
  that cited the old value is flagged for update in the same commit
  that lands the correction.
