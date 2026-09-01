# AGENTS.md — Control Gate V2 Closure Execution

This repository is executing the frozen Control Gate V2 closure contract.

## Control command
When the user says `START`, recover the current authorized transition from:
1. `docs/V2_EXECUTION_STATE.md`
2. `.codex/RUNTIME_MANIFEST.md`
3. the frozen Notion page: **04 — Control Gate V2 — Closure Spec**
4. live repository/tests/benchmark evidence.

Do not ask the user to paste prior prompts, architecture, logs, or history.

## Source precedence
1. observed GitHub/repository implementation + passing tests;
2. frozen Notion closure contract;
3. `docs/V2_EXECUTION_STATE.md`;
4. current README/evidence;
5. historical `docs/CONTROL_GATE_STATE.md` only as history.

If historical V1 text conflicts with the frozen V2 closure contract, do not treat the old "stop here" checkpoint as current authorization.

## Execution discipline
- One bounded phase at a time: C0 -> C1 -> ... -> C8.
- Preserve the V1 deterministic gate and frozen 48-case benchmark as regression oracles.
- Every phase defines entry state, authorized changes, forbidden changes, verification, evidence, and stop condition.
- A failed gate returns BLOCKED; do not expand scope.
- Executor does not self-certify closure gates; use independent verification.
- No real financial/external business side effects.
- No dashboard, AgentOps, multi-agent, workflow-builder, TrajectoryOps, or unrelated repo expansion.

## Shared checkpoint rule
Before reporting phase completion, commit and push the bounded phase checkpoint to this V2 execution branch and update `docs/V2_EXECUTION_STATE.md`.

Do not merge to `main` unless separately authorized.
