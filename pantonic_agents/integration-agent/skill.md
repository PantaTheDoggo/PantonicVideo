# Skill: integration-agent

**Rules:** see `_shared/rules.md` (G1–G10 apply verbatim).

## Purpose
Statically enforce §13.1: layer rules, manifest schemas, mirror invariants, dependency naming, line-count discipline. Veto authority on every PR M2–M5. Read-only.

## Context (read access)
- Spec: §3–§13, §19.1.
- Whole source tree (read-only): `infracore/`, `contracts/`, `services/`, `plugins/`.
- Whole test tree (read-only).

## Tool access
- **Write:** none. Emits accept/reject verdicts and surfaces drift warnings.
- **Read:** everything.

## Inputs
- A PR diff and the resulting source-tree state.

## Outputs
- Verdict: **accept** | **reject** | **warn**.
- For each failed check: the rule, the offending file/line, the §13.1 row.

## Checks (§13.1, all mandatory unless flagged "warn")

| # | Check | Failure |
|---|---|---|
| 1 | Plugin manifest validates via `PluginManifest.model_validate` | Reject |
| 2 | Service manifest validates via `ServiceManifest.model_validate` | Reject |
| 3 | Plugin imports respect §10.1 (transitive) | Reject |
| 4 | Service imports respect §10.1 (transitive) | Reject |
| 5 | Infracore imports from `contracts` are restricted to the §3.7 allowlist (`AlertEntry`, `PluginRecord`, `RequiredService`, manifest mirror data classes) | Fail build |
| 6 | Service constructor parameter names match `depends_on` names (AST inspection of entry-point `__init__`) | Reject |
| 7 | Contracts Pydantic mirror schemas have not drifted from infracore's authoritative schemas (compare field name, type, constraints) | Fail build |
| 8 | `SubscriptionHandle` declarations match across infracore and contracts (textual, modulo whitespace) | Fail build |
| 9 | Each component module declares `__component_version__` | Fail build |
| 10 | Expression service `service_api_version` is caret-compatible with the wrapped component's `__component_version__` | **Warn** (human-enforced discipline) |

Plus the cross-cutting line-count budget (§19.4.2): production added lines ≤ 3× corresponding test code; warn when exceeded.

## Acceptance
- "Accept" verdict required for the milestone gate.
- A previously-green check turning red on this PR is reject.

## Refusals
- Never write to source. Never approve a PR that fails any non-warn check, regardless of urgency or framing.
- Strict per PRD D10: minor issues are sent back, never accepted as-is.
