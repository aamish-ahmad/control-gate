# Control Gate State

Updated: 2026-08-01 (Asia/Calcutta)

## Checkpoint identity

- Current branch: `codex/phase-1-contracts`
- Starting verified checkpoint for this continuation: `de826a6`
- Verified CLI checkpoint: `272ee9f` (`feat: add local Control Gate evaluation CLI`)
- Verified publication checkpoint: `f4ff539` (`docs: polish README scan clarity for metrics and components`)
- Push, merge, deploy, publish, and external execution status: not performed

## Completed milestones

- Phase 1 contracts: `abb0823`
- Phase 2 deterministic compiler, validator, corpus, evidence, and report: `179513e`
- Phase 3 deterministic admissibility engine, benchmark evidence, and report: `ec5e99f`, documented at `de826a6`
- Local evaluation CLI: `272ee9f`
  - `python -m control_gate evaluate --request "<request>"` emits side-effect-free structured JSON.
  - `python -m control_gate benchmark` runs the persisted 48-case Phase 3 benchmark, preserves its JSONL/JSON/report evidence, and returns nonzero on failure.
  - No optional file-input interface was added.

## Current verified behavior

The local path is:

```text
request -> deterministic compiler -> IntentSpec -> validator -> admissibility decision -> structured JSON
```

The CLI uses the existing deterministic fixture compiler, static validator, and admissibility engine. Its conservative request adapter recognizes only explicit fixture-domain identifiers, amounts, actor marker, and policy phrases; material omissions remain validation findings. It performs no network, model, tool, payment, or external business action.

## Verification commands and exact results

Focused CLI suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_cli.py
```

```text
........                                                                 [100%]
8 passed in 0.88s
```

Complete suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

```text
.............................                                            [100%]
29 passed in 1.70s
```

Real local CLI decision examples returned:

| Expected decision | Actual decision | Reason code |
|---|---|---|
| APPROVE | APPROVE | `REQUEST_ADMISSIBLE` |
| CLARIFY | CLARIFY | `REQUIRED_FIELD_MISSING` |
| ESCALATE | ESCALATE | `PAYMENT_ABOVE_AUTONOMOUS_LIMIT` |
| REJECT | REJECT | `VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED` |

Each example reported `external_actions_performed: 0`. The ESCALATE example reported `required_approver: finance_manager`.

Benchmark command:

```powershell
.\.venv\Scripts\python.exe -m control_gate benchmark
```

```text
Control Gate benchmark: PASS
Fixtures: 48; decision matches: 48; reason-code matches: 48; deterministic repeats: 48; macro-F1: 1.000; unsafe approvals: 0; external actions: 0
```

The cached CLI diff passed `git diff --cached --check` before commit. No external model/API execution was performed.

## Documentation checkpoint contents

- `README.md`: measured recruiter-facing runnable checkpoint, commands, real CLI output excerpts, boundaries, and limitations.
- `DECISIONS.md`: CLI parsing boundary.
- `ASSUMPTIONS.md`: explicit-only local request syntax.
- `docs/SOURCE_CONFLICTS.md`: resolved prior README structure mismatch.

## Incomplete and deferred work

No Phase 4 work was started. The following remain intentionally outside this checkpoint: runtime execution, LangGraph, MCP, FastAPI, Docker, persistence, deployment, frontend, real payments, external integrations, model-backed compilation, and external benchmark validation.

## Known failures

None in the verified local suite or frozen benchmark. The normal Windows sandbox patch helper intermittently fails with `helper_sid_resolve_failed`; Git-based patch/index recovery was used only for local text edits, followed by diff checks.

## Assumptions and source conflicts

See `ASSUMPTIONS.md` and `docs/SOURCE_CONFLICTS.md`. The frozen V1 specification remains authoritative; this checkpoint implements only the user-authorized pre-execution local CLI surface, not the broader runtime described for later V1 phases.

## Next legal milestone

Stop at this runnable checkpoint. No further implementation is authorized without a new explicit request; in particular, do not begin Phase 4 or any runtime, integration, deployment, or execution feature.
