# Control Gate State

Updated: 2026-08-01 (Asia/Calcutta)

## Checkpoint identity

- Current branch: `feat/recruiter-facing-runtime-demo`
- Starting verified checkpoint for this milestone: `0864d88`
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
- Recruiter-facing governed execution handoff:
  - `examples/governed_execution_handoff.py` calls the real compiler, validator, and admissibility engine.
  - Only APPROVE reaches one safe, in-memory mock staging function.
  - CLARIFY, ESCALATE, and REJECT return control information without invoking staging.
  - Every route reports zero external actions and preserves intent ID/version linkage.

## Current verified behavior

The local path is:

```text
request -> deterministic compiler -> IntentSpec -> validator -> admissibility decision -> structured execution handoff
```

The CLI and governed handoff example use the existing deterministic fixture compiler, static validator, and admissibility engine. The conservative request adapter recognizes only explicit fixture-domain identifiers, amounts, actor marker, and policy phrases; material omissions remain validation findings. The handoff example adds one local fictional in-memory staging function after APPROVE. It performs no file write, network, model, payment, supplier modification, or external business action.

## Verification commands and exact results

Focused CLI suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_cli.py
```

```text
........                                                                 [100%]
8 passed in 0.88s
```

Focused governed handoff suite:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe -m pytest -q tests\test_governed_execution_handoff.py
```

```text
....                                                                     [100%]
4 passed in 0.78s
```

Complete suite:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

```text
.................................                                        [100%]
33 passed in 6.76s
```

Governed handoff route verification:

| Expected decision | Actual decision | Local staging invoked | Intent link valid | External actions |
|---|---|---:|---:|---:|
| APPROVE | APPROVE | yes | yes | 0 |
| CLARIFY | CLARIFY | no | yes | 0 |
| ESCALATE | ESCALATE | no | yes | 0 |
| REJECT | REJECT | no | yes | 0 |

CLARIFY returned clarification questions, ESCALATE returned `required_approver: finance_manager`, and REJECT returned `VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED`. Only APPROVE returned the local fictional `stage_invoice_locally` handoff.

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

- `README.md`: governed pre-execution framing, runtime boundary, measured handoff example, commands, and honest limitations.
- `examples/governed_execution_handoff.py`: deterministic local fictional execution handoff.
- `tests/test_governed_execution_handoff.py`: focused APPROVE/non-APPROVE routing, linkage, JSON, and zero-external-action tests.
- `docs/internal/decisions.md`: CLI parsing boundary.
- `docs/internal/assumptions.md`: explicit-only local request syntax.
- `docs/SOURCE_CONFLICTS.md`: resolved prior README structure mismatch.

## Incomplete and deferred work

No generalized or external execution runtime was started. The following remain intentionally outside this checkpoint: LangGraph, MCP, function-calling providers, FastAPI, Docker, persistence, deployment, frontend, real payments, external integrations, model-backed compilation, and external benchmark validation.

## Known failures

None in the verified local suite or frozen benchmark. The normal Windows sandbox patch helper intermittently fails with `helper_sid_resolve_failed`; Git-based patch/index recovery was used only for local text edits, followed by diff checks.

## Assumptions and source conflicts

See `docs/internal/assumptions.md` and `docs/SOURCE_CONFLICTS.md`. The frozen V1 specification remains authoritative; this checkpoint implements only the user-authorized pre-execution local CLI surface, not the broader runtime described for later V1 phases.

## Next legal milestone

Stop at this recruiter-facing governed handoff checkpoint. No further implementation is authorized without a new explicit request; in particular, do not add a generalized runtime, integration, deployment, or external execution feature.
