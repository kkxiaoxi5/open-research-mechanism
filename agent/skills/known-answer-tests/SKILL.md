---
name: known-answer-tests
description: Design checkers and synthetic worlds whose correct answer is known in advance. Use before any leaf is opened, and whenever a tool or algorithm is proposed.
roles: [coordinator, reviewer]
---

# Known-answer tests

No leaf is opened without a checker named in advance, and no tool is
accepted until it passes tests whose answers were fixed before it ran.

## Designing a checker

1. **The checker recomputes; it never re-reads.** It takes the leaf's
   declared arguments and produces the verdict from first principles
   (closed form, brute force on a small case, an independent method),
   never by parsing the worker's derivation.
2. **Fix the checker before the answer exists.** The checker's name and
   arguments are written on the claim card at opening time. Changing a
   checker after seeing an answer is recorded as a new trial.
3. **Include a negative control**: a deliberately wrong answer must
   fail the checker. A checker that has never failed anything is
   assumed broken.
4. **State the checker's own limits**: the range of arguments where it
   is exact, where it is approximate (and the tolerance), and where it
   saturates and must refuse rather than guess.

## Synthetic worlds

When reality cannot supply ground truth, build a small world where
the mechanism is written by you and the answer is therefore known:
the generator's parameters are the answer key. Rules:

- Results measured in a synthetic world are **calibration**, never
  evidence about the real world; cite them only as "the method behaves
  correctly/incorrectly under known conditions".
- Every synthetic world ships with the seed and the generator code, so
  any session can re-run it bit-for-bit.
- Prefer the smallest world that exhibits the phenomenon; a world you
  cannot explain by hand cannot grade anything.
