# Control Gate State

Updated: 2026-08-01 (Asia/Calcutta)

## Checkpoint identity

- Current branch: codex/phase-1-contracts
- Repository base before Phase 1: 4a42e44
- Starting verified checkpoint for this continuation: abb0823
- Current verified code checkpoint: dda9bfe
- Push/merge/deploy status: not performed

## Milestone status

### Phase 1 — complete

The seven frozen V1 contract entities, exact public enums, finance-v1 policy,
and Phase 1 acceptance tests were committed at abb0823.

### Phase 2 — partially implemented, not complete

Verified foundation committed at dda9bfe:

- nested JSON carried by immutable contracts is recursively read-only and
  serializes back to normal JSON objects and arrays;
- deterministic FixtureContext, RequestFixture, and FixtureCompiler;
- eleven stable static-validation finding families derived from the frozen
  V1 checks;
- an in-memory 48-case request catalog balanced at 12 APPROVE, 12 CLARIFY,
  12 ESCALATE, and 12 REJECT;
- deterministic compilation and static finding agreement across that in-memory
  catalog.

Phase 2 is not declared passed. Formal Phase 2 tests, committed fixture JSONL,
the benchmark runner, generated outputs, and the Phase 2 report do not exist.

Phases 3 and later were not started.

## Files in the verified code checkpoint

Commit dda9bfe:

- src/control_gate/contracts.py
- src/control_gate/compiler.py
- src/control_gate/validation.py
- src/control_gate/fixtures.py

Commit abb0823:

- docs/SOURCE_CONFLICTS.md
- pyproject.toml
- src/control_gate/__init__.py
- src/control_gate/contracts.py
- tests/test_contracts.py

## Verification commands and exact results

All verification was local and offline, using the existing .venv.

Command:

    .\.venv\Scripts\python.exe -m py_compile src\control_gate\contracts.py src\control_gate\compiler.py src\control_gate\validation.py src\control_gate\fixtures.py

Result:

    PY_COMPILE=PASS

A local smoke script compiled and validated every object returned by
build_frozen_request_benchmark() twice, compared expected static finding
families, attempted root and nested mutation, and performed an IntentSpec JSON
round trip.

Exact result:

    FIXTURES 48 {'APPROVE': 12, 'CLARIFY': 12, 'ESCALATE': 12, 'REJECT': 12}
    FINDING_MISMATCHES 0
    DETERMINISM_MISMATCHES 0
    IMMUTABILITY {'root_blocked': True, 'nested_blocked': True, 'json_round_trip': True}

Command:

    .\.venv\Scripts\python.exe -m pytest -q tests\test_contracts.py

Exact result:

    ........                                                                 [100%]
    8 passed in 2.62s

Before each checkpoint, git diff --check and/or
git diff --cached --check returned exit code 0 with no whitespace errors.

## Known failures and execution notes

- uv run pytest -q tests/test_contracts.py selected a global pytest because
  pytest is an optional dev dependency; collection failed with
  ModuleNotFoundError: No module named 'control_gate'.
- uv run --extra dev pytest -q tests/test_contracts.py timed out while
  materializing the environment. No dependency change was committed.
- The normal Windows sandbox patch/file helper failed with
  helper_sid_resolve_failed for CodexSandboxOffline (error 1332).
  Narrow elevated PowerShell and Git patch fallbacks were used and every diff
  was checked.
- An attempted benchmark.py patch failed before any file was created. No
  benchmark runner or partial benchmark artifact is present.
- No external model, paid API, business system, payment, email, push, merge,
  deployment, or publication action occurred.

## Assumptions already embodied in the partial code

- The frozen application specification governs this sprint when it conflicts
  with the broader knowledge base.
- Materially missing fixture values are represented explicitly as None or an
  unresolved goal/actor marker; the compiler does not infer them from prose.
- Fixture amounts use decimal strings and the partial benchmark uses USD; no FX
  conversion is inferred.
- The local frozen tool allowlist is invoice.parse, vendor.lookup, po.lookup,
  payment.submit, and optional audit.write.
- The local request-role allowlist is the minimum documented in ASSUMPTIONS.md;
  it is not claimed to be a general authorization model.
- Static findings are blocking inputs to a later decision engine. They do not
  themselves implement admissibility precedence.

## Source conflicts and gaps

See docs/SOURCE_CONFLICTS.md. The most important current gaps are:

- no pre-existing serialized 48-request corpus or Git history for one;
- no frozen complete reason-code taxonomy;
- no frozen total precedence for simultaneous findings;
- a high-value request with a missing approval rule is explicitly allowed to
  become CLARIFY or ESCALATE;
- no numerical Phase 2 pass threshold.

## Next legal milestone

Resume Phase 2 only:

1. add formal unit and regression tests for the existing compiler, validator,
   immutability, serialization, malformed inputs, and zero external actions;
2. serialize and commit the reviewed 48 cases as benchmarks/requests.jsonl;
3. implement the local Phase 2 runner;
4. generate outputs/phase_2/ and reports/phase_2_report.md;
5. run the Phase 2 suite and benchmark, record exact evidence, and commit only
   if the Phase 2 checkpoint passes.

Do not begin Phase 3 until that Phase 2 checkpoint is complete.
