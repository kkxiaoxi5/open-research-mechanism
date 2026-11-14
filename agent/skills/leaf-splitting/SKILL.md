---
name: leaf-splitting
description: Break a hard problem into small leaves that a checker can grade. Use when a task is too big to verify in one step, or when a worker reports stuck.
roles: [coordinator, worker]
---

# Leaf splitting（拆叶）

A leaf is the smallest unit of work whose result can be graded by a
checker that does not depend on the worker's own reasoning. If you
cannot state how a piece would be graded, it is not a leaf yet.

## Procedure

1. **State the parent claim in one sentence**, with its quantifiers and
   domain explicit. Most "unsplittable" problems are just unstated.
2. **Find the joints**: cases (by sign/size/parity/regime), lemmas the
   proof needs, computations that can be checked numerically, and the
   boundary cases where the claim is most likely to die.
3. **One leaf, one gradeable question.** Each leaf gets: the question,
   the checker (registered name + arguments), and what each outcome
   would mean for the parent.
4. **Leaves must not collide**: two leaves may not both be able to
   change the same object. Overlap is declared on the claim card, or
   the split is wrong.
5. **Order by killing power**: the leaf most likely to refute the
   parent goes first. A split that starts with the easiest piece is
   procrastination, not decomposition.

## Rules

- A leaf that comes back "split" twice in a row is re-examined by the
  coordinator: the problem statement, not the workers, is suspect.
- Splitting is itself a delivery: the split (children + rationale)
  goes on the board before any child is worked.
- Never split into more leaves than there are workers to run them in
  parallel plus a review queue of two; excess leaves are inventory,
  and inventory hides staleness.
