# 05 · Research Uncertainty: A Method for Inventing New Mathematical Tools

This framework starts from a judgment: **for genuinely uncertain objects, the machinery of classical probability theory is often not fitted to the problem.** The future is realized only once; "probability" itself is a hypothesis about the world, not an attribute the world comes with. When samples are naturally scarce, mechanisms change, and the observer sits inside the system, treating historical frequencies as the probability distribution of the future mistakes a hypothesis for a fact. This chapter is about how, facing such problems, to **invent** new mathematical tools systematically instead of applying ready-made ones.

## Prove the Boundary First, Then Look for a Method

The first step in inventing a tool is not construction but delimitation:

1. **Identifiability first**: first ask "with the information at hand, how far can this problem be answered at most?" Within a stated model class, construct observationally equivalent counterexamples: if two mechanisms produce exactly the same observable distribution, they are indistinguishable — this is not a failure; it is a theorem that saves months of wrong roads.
2. **Name the missing information**: when something is not identifiable, write explicitly "which class of information is missing to separate them" (for example: the constraint states of the acting agents, the timing of a mechanism switch). Once a gap is named, it automatically becomes a data card or a new proposition card.
3. **Negative results are assets**: a proved "cannot be separated" and a proved "can be separated" are booked and cited equally; citations must carry the model-class boundary.

## The Tool-Invention Pipeline

```
A stuck point in a real problem
  → a minimal synthetic world (fake market / fake data generator: mechanism hard-coded, answers known)
  → derive inside the synthetic world: what can be proved, where it fails (hand-written argument first, formalization after)
  → known-answer tests + mutation-must-fail tests
  → back to the real problem: only when a judgment changed does the tool count as established
  → register a tool card (principle / boundary / failure conditions)
```

- **A synthetic world is a laboratory, not an exam hall**: effect sizes obtained in a synthetic world are settings, and may never be cited as real-world estimates (see the evidence tiers in `04-evidence.md`).
- **Formalization is an amplifier**: writing an argument in machine-checkable form (theorem prover, property tests) lets one session's insight be reviewed by other sessions within minutes — this is how "adding people speeds things up" is realized on the mathematics line: one proposes, many verify and hunt counterexamples in parallel.
- **Search at scale**: candidate tools / candidate propositions are first generated in bulk, then eliminated by counterexamples; the elimination record is kept in full (what was selected, why it died) and booked together with the global trial count.

## Working Assumptions about Research Uncertainty (Replaceable per Project)

- Treat "uncertainty" itself as the research object: when distributions drift, first study **the structure of the drift** (what changes fast, what changes slowly, what has memory), instead of pretending the distribution is fixed.
- For scarce-sample big events, set weights by priors and mechanistic reasoning rather than forcing significance out of frequencies; conclusions are expressed as "which decision changes, and at what position size," not as p-values.
- The quality of predictions is measured by **scoring rules** (see Class B of the tools line); account performance, statistical evidence, and prediction quality are reported separately, and none may impersonate another through a single "multiple."
- Every tool must state its **failure conditions**: on what observation does what this tool says become void. A tool without failure conditions may not enter the tool pool.

## Relation to the Evidence Discipline

This chapter governs "how to build"; `04-evidence.md` governs "how much what is built counts for." The invention stage encourages continuous exploration and drops "run only once"; but exploration results are not written up as confirmations, and all selections and failures are registered — freedom at the exploration tier, discipline at the claiming tier.
