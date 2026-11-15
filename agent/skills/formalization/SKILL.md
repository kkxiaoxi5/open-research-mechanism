---
name: formalization
description: Turn an informal argument into a machine-checkable form (e.g. a Lean proof or a symbolic/numeric certificate). Use when a result matters enough to outlive the session that produced it.
roles: [worker, reviewer]
---

# Formalization

An argument that a machine has checked cannot be silently weakened by
retelling, cannot drift when the session ends, and can be re-verified
by any other session in minutes. Formalization is how one session's
insight becomes the team's permanent asset.

## What to formalize (in this order)

1. **Load-bearing lemmas first** — the steps other proofs stand on,
   not the headline result. A formalized lemma is reused for free;
   a formalized headline is a trophy.
2. **Any claim that has been "re-proven" by hand more than once.**
   The second re-proof is the signal: pay the formalization cost once
   instead of the re-derivation cost forever.
3. **Checker-critical identities** — the formulas your known-answer
   checkers rely on. If the checker is wrong, every verdict it issued
   is suspect; its foundations get the strongest form of checking.

## Procedure

- State the claim in the formal system *before* writing the proof;
  half of all formalization failures are the discovery that the
  informal claim was ambiguous. That discovery is a delivery in
  itself: report the ambiguity as a split of the parent leaf.
- Keep the formal artifact and the informal text side by side, with a
  line-level correspondence for the load-bearing steps. A formal proof
  nobody can map back to the argument convinces no one.
- A failed formalization attempt is recorded with where it got stuck;
  "the machine rejected step 4" is precise information about the
  informal argument, and is routed back to the author as a review
  comment, not discarded.

## Honest limits

Formalization verifies that the proof follows from the statement —
not that the statement says what you meant, and not that the premises
hold in the world. Statement review stays a human/reviewer job
(see proof-review, step 1), and premises stay in the evidence ledger.
