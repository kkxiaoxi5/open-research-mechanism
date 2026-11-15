# 04 · Evidence Discipline

The purpose of this discipline is not to slow research down, but to let **a conclusion know its own weight when it is cited**.

## Evidence Tiers (Citations Must Carry Their Tier)

| Tier | Meaning | Citation rule |
|---|---|---|
| Mathematical | Conclusions proved / derived within a stated model class | Must carry the model-class boundary; no extrapolation to reality |
| Synthetic | Verified in artificial data / a fake market | Effect sizes are settings, not real-world estimates |
| Implementation | Code and caliber independently reviewed, known-answer tests passed | Numbers may be cited, with version |
| Real statistics · exploratory | Descriptions obtained on data whose direction has been seen | May only be called "descriptions," not confirmations |
| Real statistics · confirmatory | Judged by preregistration on unexposed data or true forward records | May be called confirmation, with power and caliber |
| Execution | Fills, costs, slippage, etc. actually measured | Any cost not measured is labeled "assumed" |

## Five Hard Rules

1. **Prior power first**: compute the minimum detectable effect before looking at means (MDE ≈ 2.8 × SE; when events cluster, use the clustered variance). If MDE exceeds the predicted effect → do not start confirmatory work; exploration may continue, but conclusion strength is capped at "description."
2. **The global trial count only grows**: all trials (including failures, session changes, and repository changes) go into the same ledger; changing environments does not reset the selection history. When reporting significance, give the caliber under the global N.
3. **Exposure registry**: every dataset is labeled with its exposure state (unseen / direction seen / opened); an "opened" segment may not be used again for confirmation; confirmation can only come from unexposed segments or true forward records.
4. **Seen-direction marking**: any new design made on data whose direction has been seen must be marked as such on the deliverable, and its results may not be upgraded to confirmation — this rule guards against ourselves, not against the market.
5. **Shrinkage calibration**: estimate the project's shrinkage factor from historical pairs (development segment vs. confirmation segment); in prior power calculations, multiply the predicted effect by the shrinkage factor first. Numbers reported selectively (good news only) are always cited after shrinkage.

## Known Answers, and Mutation Must Fail

- New code first passes **known answers** (small examples computable by hand) before touching real data.
- Every key module carries **mutation-must-fail** tests: deliberately introduce an error in one place, and the test must turn red; a test that cannot turn red is not a test. Cross-line mutation bills are a valid form of peer review.

## Forward Records

- Once the historical exam papers are used up, the only source of confirmation is the **true forward**: register the event definition, the data-fetch time, and the scoring rule in advance; land records daily with timestamps; scoring is done by a non-author.
- A forward channel must have a **named maintainer** and landing checks; with no maintainer, write "not started" — a "planned record" may not be written as "recording in progress."
- The confirmation cycle of a forward record is counted in events, not prodded by the calendar; how many events the power calculation requires is written into the registry page.

## Cost and Execution Caliber

- The backtest caliber (fees, slippage, fill assumptions) is versioned by the project owner; changes require a rerun and a version label.
- Before costs are actually measured, cited conclusions must carry the "costs assumed" label; conclusions sensitive to cost (net/gross ratio near 1) are listed separately and re-reviewed first when the measured caliber arrives.

## Citation Forbidden Zones (Self-Deception Guards at the Writing Level)

Sentence patterns forbidden in closing pages and reports (reference list, extend per project):

- Writing "not answered" as "excluded," or "not detected" as "does not exist."
- Supporting a confirmatory-tier conclusion with an exploratory-tier descriptive number.
- Citing numbers without a stated caliber (per-trade / per-cluster, gross / net, which data segment).
- Writing "planned to do" as "doing," or "read" as "received."
