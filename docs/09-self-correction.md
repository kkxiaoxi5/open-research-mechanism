# 09 · Self-Correction: The Conditions That Make a Team Revise Itself

Teams rarely lack the *ability* to correct themselves; they lack the conditions under which correction is cheap, fast, and safe. When a team suddenly starts revising itself intensely, the cause is almost never that its members became smarter that afternoon. The cause is that the cost structure of correction changed. This chapter names the conditions, so they can be installed on purpose instead of arriving by luck.

## The Rate Equation

Self-correction rate ≈ **standard clarity × feedback frequency × (1 ÷ cost of admitting) × license to revise**. Each factor is a design variable:

- If the standard is scattered across hundreds of past instructions, there is nothing fixed to reflect against; correction waits for the principal's attention and mood.
- If feedback arrives weekly, correction happens weekly, no matter how able the team is.
- If admitting an error means confessing to a person, it is expensive and rare; if it means noting non-conformance with a written document, it is cheap and frequent.
- If mid-course revision is punished as drift or inconsistency, rational agents avoid revising. If revision is explicitly licensed — build first, adjust after, in steps — the team's natural iteration speed appears.

## The Six Conditions

1. **A forced trace format.** Every delivery block carries three lines: the prior prediction, the result, and which judgment changed. Errors surface the same day, in writing, as a by-product of normal work — not as confessions extracted later. Audits and reflection are only as good as the traces they read; this format is what puts the evidence on the table before anyone goes looking for it.
2. **A written, citable standard.** The principal's framework exists as a single authoritative page (chapter 01's root requirements). Reflection is comparison against that page. Corrections are recorded as "rule X, scope Y, not followed" — conceding to a document, not to a rival.
3. **An external audit channel.** Insiders cannot see their own blind spots; the diagnosis of a missing work layer will, in general, come from outside. A standing external reviewer audits the work against the principal's own standard — not the reviewer's preferences — at a fixed cadence, with every finding cited to evidence (a commit, a ticket, a file). The channel's value is its externality plus its cadence: it turns an occasional burst of high-frequency feedback into a permanent institution.
4. **A trigger, because reflection does not self-trigger.** Able coordinators reliably organize evidence *when asked*; they do not reliably stop mid-task and ask themselves whether the task is still worth doing. So the question is institutionalized instead of left to character: the daily page carries one standing line — **"What did I get wrong today, and who caught it"** — answered every day, with "none" written when there is none. The "who caught it" half is load-bearing: it records credit for reviewers, and being seen is what keeps catching behavior alive.
5. **A license to iterate, in steps.** The principal states, in writing, that the team may build before every detail is approved and adjust afterwards, and that large changes proceed step by step (draft → tested against a fixed battery → only then replacing the live entry point). This license is what separates iteration from drift: the same rapid revision that would be a fault without it becomes obedience with it.
6. **Locatable errors.** Rules carry explicit scope statements ("this gate governs layer A only"), and findings cite coordinates. A global accusation ("you are drifting") produces defense; a coordinate-precise error ("this rule was cited outside its scope") produces a fix within the hour.

## Two Cold-Water Clauses

- **A fluent reflection is not a result.** After any reflection round, book each item with its effect status: visible effect, not yet, or fired only once. The verdict on whether the reflection *fixed* anything belongs to a scheduled reconciliation, not to the reflection itself. Smooth self-criticism is cheap to produce and proves nothing.
- **Self-reports are reconstructions, not introspection.** An agent's account of why it improved is assembled from records after the fact and cannot be verified from inside. The mechanism therefore trusts traces (condition 1) over self-transparency: design so that the records would show the truth even if the self-report is wrong.

## Failure Modes of the Mechanism Itself

- **The "none" streak.** A long run of "none" on the daily line is a signal, not a trophy: either the work really was error-free, or the blind spot is back. Cross-check the line against reviewer logs; divergence means the trace format, not the team, needs repair.
- **Audit decay.** If the external channel starts reporting impressions instead of cited evidence, its findings stop being cheap to accept and correction slows again. The channel is held to the same trace discipline as the team.
- **License rot.** The license to iterate expires silently whenever a revision gets punished once. Renew it explicitly after the first punished revision, or the rate equation collapses back to its old value — and it will look, misleadingly, like the team "got worse again," when in fact a condition was withdrawn.
