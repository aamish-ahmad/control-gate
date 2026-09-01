# Control Gate V2 Execution State

Updated: 2026-09-02 (Asia/Kolkata)

## Controller status
Status: C1_PASS_AWAITING_CONTROLLER
Completed phase: C1 — deterministic local supplier/PO/invoice/policy tool environment
Next phase: pending controller verification and explicit authorization
Execution branch: `v2-closure-execution`
Frozen baseline `main` SHA: `6c48d6449080b0e036025cb305b2c590b00737a4`

## Why this file exists
The previous `docs/CONTROL_GATE_STATE.md` is a historical V1 checkpoint dated 2026-08-01. Its "stop here; no generalized runtime authorized" instruction described that older sprint and is not the current V2 authorization.

Current V2 authorization is the frozen Notion page **04 — Control Gate V2 — Closure Spec**.

## C0 entry state
Known shared facts:
- public repo: `aamish-ahmad/control-gate`;
- current `main`: `6c48d6449080b0e036025cb305b2c590b00737a4`;
- current README reports 36 passing automated tests;
- frozen benchmark remains 48 cases;
- no V2 runtime implementation is yet claimed;
- no merge/deploy/publication is authorized by C0.

## C0 authorized actions
1. verify the six generic global skills are present/readable;
2. verify local checkout tracks current `origin/main` baseline;
3. run the complete existing test suite;
4. run the frozen 48-case benchmark;
5. record exact commands/results and baseline hashes/checksums where practical;
6. inspect existing repo-local instructions for conflicts;
7. preserve V1 deterministic semantics and benchmark inputs unchanged;
8. update this file with C0 evidence;
9. run independent verification;
10. commit + push the C0 shared checkpoint on `v2-closure-execution`.

## C0 forbidden actions
- no C1 tool environment implementation;
- no LangGraph/FastAPI/MCP/runtime feature work;
- no redesign of V1 compiler/validator/admissibility;
- no benchmark edits;
- no merge to main;
- no deployment/publication;
- no unrelated cleanup.

## C0 PASS condition
C0 passes only if:
- global runtime prerequisite is verified;
- local baseline matches the frozen main checkpoint or any divergence is explicitly reconciled;
- full existing tests pass;
- frozen 48-case benchmark passes unchanged;
- runtime manifest/state ledger exist;
- independent verifier returns PASS;
- shared C0 checkpoint is pushed to this branch.

## C0 execution evidence
Observed on 2026-09-02 from branch `v2-closure-execution`:

- branch entry checkpoint: `5eeefe56cb8e517e054cd0f9e45d5c941c953294`;
- verified C0 evidence commit: `abe2acaf96aed361fbcac8c41216f73801490f1c`;
- branch tracks `origin/v2-closure-execution` and is based on frozen `origin/main` SHA `6c48d6449080b0e036025cb305b2c590b00737a4`;
- the only branch changes before C0 evidence recording are the three shared handoff files: `AGENTS.md`, `.codex/RUNTIME_MANIFEST.md`, and this ledger;
- no differences from `origin/main` exist under `src/`, `tests/`, `benchmarks/`, `outputs/`, `reports/`, `README.md`, or `pyproject.toml`;
- the six required generic global skills are present and readable in the active Codex skill root: `trajectory-alignment-controller`, `transition-commit-gate`, `trajectory-resource-router`, `trajectory-prompt-compiler`, `bounded-executor`, and `independent-verifier`;
- their respective `SKILL.md` SHA-256 values are `bc818da1910ecac2b88390239b6f5799c9c145226224220ab501d7d12667fa73`, `0df2a006ebeb29887ba9e17686a008c2e7253140f403d485758e5770c8a268a9`, `94b42e3c70d26100e2ba22d2328a77b2a6aae94fa785efbbd0f17867b52a9a0b`, `1b42dacd4f4200eb68996167701f918a17db15cb77983a7673d9acfb16ba2cfd`, `9ad24e410db0c69180e971536d43591f65ec2071477c9c9b77fe5404226ef6f3`, and `b9dc389eac899208c10400834c9bb1a6463dd75e46e1b9c863a2b7c0fbb30ea6`;
- full-suite command: `./.venv/Scripts/python.exe -m pytest -q` -> `36 passed in 4.38s`;
- frozen-benchmark command: `./.venv/Scripts/python.exe -m control_gate benchmark` -> PASS with 48 fixtures, 48/48 decision matches, 48/48 reason-code matches, 48/48 deterministic repeats, macro-F1 1.000, 0 unsafe approvals, and 0 external actions;
- frozen input SHA-256: `benchmarks/requests.jsonl` = `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`, identical to `origin/main`;
- the verification commands left the repository worktree unchanged before this ledger update;
- independent C0 verification returned `VERIFIED` against the precommitted C0 conditions.

C0 is PASS. C1 is authorized only after this ledger update is committed and pushed as the shared C0 checkpoint.

## C1 phase contract

### Entry state
- C0 shared checkpoint is pushed at `74db7c528198d3fbe2cf63ed4dda0d0617fb8959`;
- local `v2-closure-execution` matches `origin/v2-closure-execution` at entry;
- C1 is explicitly authorized by the frozen Notion controller checkpoint;
- the existing 36-test V1 suite and frozen 48-case benchmark pass at entry.

### Authorized changes
- deterministic synthetic supplier, purchase-order, invoice, policy, approval-threshold, duplicate-index, and staged-action fixtures;
- bounded local implementations of `lookup_supplier`, `lookup_purchase_order`, `inspect_invoice`, `check_duplicate`, `retrieve_policy`, `stage_payment`, and `request_human_approval`;
- focused tool-level tests;
- this C1 state/evidence update.

### Forbidden changes
- no agent loop or orchestration framework;
- no Gate B/runtime admissibility;
- no human interrupt/resume or approval-resolution runtime;
- no retry/recovery or memory work;
- no FastAPI, MCP, Docker, CI, persistence, experiment, dashboard, or external service work;
- no real financial or other external business side effects;
- no changes to V1 compiler, validator, admissibility semantics, frozen benchmark inputs, or historical evidence.

### Verification conditions
- all seven required C1 tools exist and operate only on deterministic local state;
- records are immutable and fixture instances do not share staged mutable state;
- missing, malformed, inconsistent, inactive, duplicate, over-limit, or wrong-currency actions fail closed with stable error codes;
- valid staging is idempotent, fully linked, explicitly local simulation, and records zero external actions;
- human approval requests are idempotent pending local records and perform zero external actions;
- focused C1 tests, the complete suite, and the frozen 48-case benchmark pass;
- protected V1 and benchmark surfaces remain unchanged;
- independent verification returns `VERIFIED` before C1 is marked PASS.

## C1 execution evidence
Observed on 2026-09-02 from the C1 candidate worktree:

- verified C1 evidence commit: `7ba31fd49128c16df254db8523f3ca3cbb4ae87c`;
- implementation: `src/control_gate/tool_environment.py`;
- focused tests: `tests/test_tool_environment.py`;
- focused command: `./.venv/Scripts/python.exe -m pytest -q tests/test_tool_environment.py` -> `20 passed in 2.50s`;
- complete-suite command: `./.venv/Scripts/python.exe -m pytest -q` -> `56 passed in 5.31s`;
- frozen-benchmark command: `./.venv/Scripts/python.exe -m control_gate benchmark` -> PASS with 48 fixtures, 48/48 decision matches, 48/48 reason-code matches, 48/48 deterministic repeats, macro-F1 1.000, 0 unsafe approvals, and 0 external actions;
- Python compile check passes for the C1 implementation and focused tests;
- no protected V1 source, test, benchmark, or evidence file is modified;
- independent C1 verification returned `VERIFIED` against the precommitted C1 conditions.

C1 is PASS. C2 remains unauthorized until the controller verifies the shared checkpoint and explicitly advances the ledger.

## Next legal transition
Current authorized transition: finish and checkpoint C1 only.

After C1 PASS, stop for controller verification and authorization. C2 is not self-authorized by the executor.

If any C1 invariant fails: return BLOCKED with evidence and authorize only the smallest repair needed for C1.
