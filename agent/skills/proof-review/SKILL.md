---
name: proof-review
description: Review a proof or derivation as a non-author. Use for every review assignment; the reviewer recomputes and re-derives, never proofreads.
roles: [reviewer]
---

# Proof review

The reviewer is not a proofreader. The reviewer's job is to try to
make the argument fail, in the cheapest places first, and to close
the leaf only as proven / refuted / split.

## Procedure

1. **Duiti first**: restate, in your own first line, the exact claim the
   leaf was opened with (copied from the claim card, not from the
   delivery). If the delivery proves a different claim — a weaker one,
   a special case, a converse — that is a refutation of *this* leaf,
   however nice the other result is.
2. **Check the ends before the middle**: verify the statement's
   boundary cases and the final step's use of the lemmas. Most broken
   proofs are broken at the seams.
3. **Recompute every load-bearing number** with the leaf's checker.
   A single number that the whole argument stands on gets recomputed
   twice, by two different routes if they exist.
4. **Hunt the hidden premise**: list every fact the proof uses that is
   not in the claim's premises ("clearly", "obviously", "standard"
   are the markers). Each unlisted premise either gets cited to a
   closed leaf or becomes a new leaf.
5. **Mutation pass**: mentally break one hypothesis at a time and ask
   where the proof would notice. A step that no hypothesis-breaking
   can disturb is decoration, and decoration hides gaps.

## Closing rules

- **Proven**: you re-derived or checker-verified every load-bearing
  step, and your own counterexample pass (boundaries at minimum)
  found nothing.
- **Refuted**: you exhibit the failing case or the exact step that
  does not follow. "Seems wrong" is not a verdict.
- **Split**: the argument is sound modulo a named missing lemma; the
  lemma becomes a child leaf with its own checker.
- You may not close a leaf you authored, and you may not soften a
  verdict because the result is wanted. Record pressure if it happens;
  that, too, is data.
