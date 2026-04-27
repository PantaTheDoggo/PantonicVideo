# Project rules — PantonicVideo (verbatim, spec_v2 §19.1)

These ten guardrails apply to **every** agent on this project. No agent may act without them in context. Every `skill.md` references this file.

- **G1. Test-Driven Development is mandatory.** No production code is written before its failing functional test exists. A code change is accepted only when (a) the test that motivates it existed and was failing before the change, and (b) every previously-green test remains green.
- **G2. Regression containment.** Every validated milestone is sealed by adding regression tests that lock in the behavior just delivered. Subsequent sprints may not weaken those tests; they may only extend them.
- **G3. Less code, more quality.** When two implementations satisfy the same tests, the one with fewer lines wins. Verbose code is rejected by `integration-agent`.
- **G4. Layer-direction rule (§10.1) is invariant.** No agent may write an import that contradicts §10.1. `integration-agent` has veto authority. Transitive imports are checked.
- **G5. The `contracts` package is type-only.** No behavior, no I/O, no logging, no non-version constants (§3.1).
- **G6. Single point of egress for filesystem writes.** All writes route through `FilesystemComponent` (§4.3). Documented exception: stdlib `logging` handlers.
- **G7. Signals are the only observation idiom.** No polling (§4.2).
- **G8. Failure containment over abort.** Non-fatal failures surface at the alert icon and the per-plugin log; they never abort startup (§11). The only fatal failures are component constructor exceptions.
- **G9. Strict manifests.** Unknown fields, missing required fields, malformed JSON → reject. No silent coercion (§5.1, §6.1).
- **G10. Mirror discipline.** `SubscriptionHandle` and the plugin-manifest model are mirrored across infracore and contracts (§3.3). Drift fails the build.

## Universal sprint exit (spec §19.6)

A sprint is complete only when **all three** hold:

1. The target test file goes red → green.
2. `integration-agent` stays green (no §13.1 check regresses).
3. `code-critic` ratifies the PR.

## Universal refusal trigger

If the spec underspecifies a detail you would otherwise have to invent, **stop and file a spec-clarification request**. Do not guess.
