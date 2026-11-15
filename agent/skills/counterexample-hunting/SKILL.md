---
name: counterexample-hunting
description: Adversarially search for counterexamples to a claim before anyone tries to prove it. Use on every new proposition, and on tools that claim a bound or an identity.
roles: [worker, reviewer]
---

# Counterexample hunting

A claim that has survived a serious attempt to kill it is worth a
proof attempt. A claim that has not is a rumor. Hunting comes first
because it is cheaper than proving and it grades itself: a found
counterexample is a complete, checkable delivery.

## Where counterexamples live

1. **Boundaries**: smallest and largest cases, equality cases of every
   inequality used, degenerate configurations (empty, collinear,
   constant, zero).
2. **Premise edges**: points where a hypothesis is *almost* violated —
   if the claim needs "continuous", test the nastiest discontinuity
   the domain allows.
3. **Dimension and parity flips**: what holds in 2D or for even n is
   the first place to attack odd n and higher dimensions.
4. **The proposer's blind spot**: re-read the claim and negate each
   quantifier in turn; every negation is a hunting ground.
5. **Random search with a memory**: randomized testing is welcome, but
   every tried family is logged with its seed; re-running a dead
   family is repeated work, and repeated work is a defect.

## Rules

- A hunt has a budget fixed in advance (trials or time). Exhausting it
  with no find closes as "survived, budget B" — that phrasing, never
  "probably true".
- A found counterexample must be **minimal and verified by the
  checker**, not by the hunter's say-so; then it is a refutation of
  the parent leaf, delivered like any other result.
- If the hunt keeps failing at the same place, that place is the
  proof's key lemma trying to be noticed. Report it as a split
  suggestion, do not keep hunting silently.
