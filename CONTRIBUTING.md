# Contributing

Contributions that improve **the mechanism itself** are welcome. This repository accepts only mechanism-level contributions — no content from any specific domain (data, strategies, conclusions, or any project's internal documents).

## Contribution process (using this framework's own rules)

1. **Write a prior prediction first**: when opening an issue or PR, state which failure mode the change addresses (drift / duplicated labor / abandonment halfway / adding people does not speed things up) and which behavior will change once it is in.
2. **Authors do not review their own work**: a PR needs at least one non-author reviewer; changes to the rules need two.
3. **Known answers first**: code changes under `reference/` must come with tests; a new test must be able to answer "if I deliberately break one spot, does it catch it?"
4. **Keep failures**: do not delete rejected proposals. Move them to `docs/rejected/` with the reason for rejection and the reopening condition.

## Style

- Write rules as checkable sentences: a third party should be able to point at one and ask, "was this actually done?"
- When quoting a proposer's words, quote verbatim and give the source; paraphrases must be marked as paraphrases.
- Documents, prompts, and the console UI are in English, with Japanese versions alongside; Chinese is kept in the README only.
