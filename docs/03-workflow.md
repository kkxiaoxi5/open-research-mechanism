# 03 · Workflow: From Proposition to Receipt

## Overview

```
Proposition (with prior prediction) → split into small leaves → claimed on the claim board → execution → delivered with a delivery block
      → independent review (recomputation / blind read-back / mutation test) → registered at the intake → the changed judgment written into the daily page
```

## Propositions and Prior Predictions

- Before work starts, each proposition states clearly: what it is to answer, what the prediction is (with an order of magnitude), what result counts as proven, what result counts as refuted, and whether the power suffices (see `04-evidence.md`).
- Predictions must be submitted **before** results are seen (the version history's timestamps serve as witness).
- A proposition with insufficient power may be explored, debugged, and recorded, but may not be written up as a confirmation or a refutation.

## Splitting into Small Leaves (The Key to Parallelization)

- Split a big problem into **small questions with machine-checkable verdicts (small leaves)**: each piece has explicit inputs, an explicit deliverable, and explicit automatic criteria (known answer / unit test / bit-for-bit reproduction), so an executor who does not know the whole problem can still complete it independently.
- Small leaves are the vehicle of "adding people speeds things up": the dispatch time is recorded, and delivery and acceptance times are taken from channel messages — that set of timestamps is the measure of the scaling effect.
- Splitting principle: prefer splitting out **Class A (representation & derivation)** small leaves, rather than making Class B judging tools ever thicker.

## Claim Board

The minimal structured carrier of task state (reference implementation: `reference/claimboard.py`):

- An **append-only** event log (JSONL), sharing the same lock as the evidence ledger, so concurrent writes cannot corrupt it.
- Event types: `open` (assign), `claim` (claim), `deliver` (deliver), `accept` (accept), `reject` (return), `split` (split smaller), `note` (remark).
- Required when assigning: source (proposition ID), prior prediction, acceptance method.
- Required when delivering: the result, and **which judgment changed because of it**.
- **Outcomes have only three values**: proven / refuted / split. Closing with "cannot determine" is rejected; when genuinely stuck, the stuck point must be explained in no more than three sentences, and a different-angle child problem is generated automatically; "can only wait" tasks must carry a different-angle child problem — empty waiting is not allowed.

## Delivery Block

Every deliverable opens with a fixed five sections (template: `templates/delivery-block.md`):
task and specification version / conclusion / evidence status (labeled by tier) / deliverable paths and reproduction commands / remaining gaps and the next receiver.

## Review

- Reviewers are assigned from outside the authors; one reviewer reviews no more than 2 items at a time (to keep backlog from masquerading as "under review").
- Three review methods, combined as needed:
  - **Independent recomputation**: a different person (or a different model) recomputes from the raw inputs, aligning bit-for-bit or within tolerance.
  - **Blind read-back / question matching**: looking only at the problem and the user's original words, check whether the deliverable answers the question that was actually asked (guarding against "answering a different question than the one posed").
  - **Mutation test**: deliberately break one place in the deliverable and see whether the test suite catches it; the fraction it misses is the true reading of test strength.
- Review verdicts are graded: accept / accept with conditions (conditions listed) / return (missing items listed). Until all conditions are closed, the deliverable may not be cited downstream as confirmed.

## Closing Out

- The conditions for closing a problem are written down in advance (for example: the main diagnostic has run and been accepted, the correction page confirmed, the closing page accepted).
- The closing page must state honestly: **what was answered, what was not answered**, what the forward record still needs to track, who the maintainer is, and what the reopening conditions are.
- Closing out ≠ refuting the problem. Parts not answered are written as "not answered," not "excluded."
- After closing, the problem keeps only maintenance work and no longer occupies main-line research time, unless a reopening condition triggers.
