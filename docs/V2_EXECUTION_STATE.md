# Control Gate V2 Execution State

Updated: 2026-09-08 (Asia/Kolkata)

## Controller status
Status: C3_PASS_AWAITING_CONTROLLER
Completed phase: C3 — Gate B over the existing C2 trajectory
Verified implementation checkpoint: `6ef6f96b88650a192241b85c1148cf4a6142ac9d`
Active phase: none; C3 authority ends at the shared checkpoint
Next phase: C4 requires separate controller authorization
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
Current authorized transition: publish the independently verified C3 evidence checkpoint only. No further implementation phase is authorized.

The historical C1/C2 stops are superseded for C3 only. Do not start C4.

If a gate fails, preserve evidence and return BLOCKED without expanding scope.

## C2 phase contract — committed before implementation

- SOURCE_SCOPE: existing contracts in `src/control_gate/contracts.py`, a bounded runtime in `src/control_gate/invoice_runtime.py`, new focused `tests/test_invoice_runtime.py`, the runtime dependency in `pyproject.toml`, and C2 evidence in this ledger and `reports/c2/`.
- Entry: clean local HEAD and fetched `origin/v2-closure-execution` both equal `5c79b649e1d3262656bf33d0826bb3abe15a8d86`; frozen `origin/main` remains `6c48d6449080b0e036025cb305b2c590b00737a4`. Live Notion page `3c0d086d-0fe9-81ec-9e0f-c28b316836e1`, section 18, confirms C1 independently verified and C2 authorized. Older closing checkpoints are history.
- D: an inspectable stateful local supplier-invoice trajectory reusing the existing plan/run/event/outcome contracts, with Gate A controlling entry, actual C1 tool calls, immutable intent/version/plan linkage, observation-driven advancement, and an evidence-backed terminal outcome.
- ALLOWED: additive runtime-state fields and the missing RuntimeDecision interface; one fixed-domain LangGraph controller; direct C1 tool integration; new C2 tests; bounded dependency installation; evidence recording; independent read-only verification; commit and push to the execution branch. LangGraph supplies scheduling and conditional transitions, with no model, checkpointer, external tracing, or service. Independent verification is build-time separation, not a product multi-agent runtime.
- FORBIDDEN: changes to existing V1 authorization semantics, existing regression tests, C1 tools, benchmark inputs or historical generated evidence; Gate B enforcement; human interrupt/resume or approval resolution; retry/recovery/memory expansion; service/deployment/CI/experiments; real business side effects; merge to main; C3.
- OUTPUT: runtime implementation, focused tests, one JSON trajectory in `reports/c2/`, independent verification evidence, and this updated ledger on the pushed branch.
- V1: existing 56 tests and frozen 48-case benchmark pass unchanged; benchmark SHA-256 remains `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`.
- V2: APPROVE executes the real bounded tool trajectory and produces one local staged payment; CLARIFY/ESCALATE/REJECT invoke no tools and retain Gate A reasons/questions without implementing human continuation.
- V3: plan, run, action/event, observations, and outcome preserve run/intent/version/plan identity; tool evidence and state changes are inspectable and serializable; separate runs do not share mutable state.
- V4: next actions depend on recorded observations; expected tool failures terminate without staging or retry; terminal outcomes cannot be replayed through the controller; outcomes claim only supported authorized success conditions. RuntimeDecision remains an unused C3 interface, not a fabricated runtime approval.
- V5: focused C2 tests and full suite pass; a separately instructed verifier checks the committed conditions, protected diff, tests, benchmark, and trace before PASS. New focused tests supplement rather than replace the unchanged regression oracle.
- STOP: VERIFIED plus pushed C2 checkpoint, or a genuine trajectory-changing blocker. C3 remains unauthorized.

### C2 entry evidence

- `./.venv/Scripts/python.exe -m pytest -q` → 56 passed in 6.00s.
- `./.venv/Scripts/python.exe -m control_gate benchmark` → PASS; 48 fixtures, 48 decision matches, 48 reason matches, 48 deterministic repeats, macro-F1 1.000, unsafe approvals 0, external actions 0.
- Six required global skills read and bound to Control Gate; native local execution and Notion read access used. No prior-project state was adopted.

### C2 candidate evidence — 2026-09-08

- Precommitted phase/verification contract: `5386009`.
- Implementation: additive fields on the existing `ExecutionRun`, linked `RuntimeDecision` interface, and `src/control_gate/invoice_runtime.py`. The existing `IntentSpec`, `ExecutionPlan`, `PlanStep`, `TrajectoryEvent`, and `RunOutcome` are reused. `HumanIntervention` is retained unchanged for C4.
- Commodity scheduling: LangGraph `1.2.11` (Python >=3.10), pinned in the optional `runtime` extra. Install with `python -m pip install -e ".[dev,runtime]"`. No model or network access is needed for execution; external tracing is disabled.
- Reproduce: `python -m control_gate.invoice_runtime` emits the complete run as JSON. `--request` accepts a supplier-invoice request through the existing compiler and Gate A. Non-APPROVE invokes no tools; CLARIFY/ESCALATE retain their nonterminal Gate A state with no continuation API.
- Actual C1 tools: inspect invoice → supplier lookup → PO lookup → duplicate check → policy retrieval → local payment staging. Observations drive later arguments and advancement. Input/record mismatch and duplicate observations stop the fixed workflow. Existing C1 staging enforces its own unchanged guards; no generic Gate B exists.
- `./.venv/Scripts/python.exe -m pytest -q tests/test_invoice_runtime.py --tb=short` → 23 passed in 60.62s.
- `./.venv/Scripts/python.exe -m pytest -q --tb=short` → 79 passed in 83.65s (original 56 plus 23 C2 cases).
- `./.venv/Scripts/python.exe -m control_gate benchmark` → PASS; 48/48 decisions, reasons and deterministic repeats; macro-F1 1.000; unsafe approvals 0; external actions 0.
- Frozen input SHA-256 remains `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`.
- Trace: `reports/c2/supplier_invoice_trajectory.json`; COMPLETED; six tools; 16 events; one staged local payment; zero external actions; serialized run validates back to the same existing contract. SHA-256: `9a216c8bb577efb44dcfe086cf603970b07d291a2036772d55be76fd410bd11d`.
- Initial focused tests exposed a frozen nested-JSON revalidation error during incremental evidence updates. The runtime now uses the existing serializer before validated reassignment; the final focused/full runs above pass. Existing regression tests and frozen JSON helpers were not changed.
- Limits: deterministic controller, local fixtures and staging only; RuntimeDecision remains null; no Gate B, human continuation, recovery, service, persistence backend, or experiment claim. Unknown success conditions are not claimed as satisfied.
- Independent verification and shared push are pending. C3 remains unauthorized.

### C2 independent-review repair evidence — 2026-09-08

- Initial implementation checkpoint: `8cc74eb0a4295c8844b6e0032630986fda563d91`.
- Independent review reproduced a V3 defect: a rejected after-model link check could leave a mismatched event assigned. This was an implementation defect within the committed C2 target, not a change to its desired state or scope.
- Repair: link validation now occurs on fields before mutation. Rejected event, outcome, and runtime-decision assignments leave the entire serialized trajectory unchanged. Existing frozen identity fields remain immutable.
- Focused C2 tests: 26 passed in 41.19s; complete suite: 82 passed in 33.17s. Three new regression cases cover the independently observed integrity defect. Existing V1/C1 tests are unchanged.
- Regenerated trace after repair: `reports/c2/supplier_invoice_trajectory.json`, SHA-256 `c03230b0fbf7e8e1b25292219c89ee09133a2cad228c160b1852d06a54718083`; COMPLETED, six calls, 16 events, one local stage, zero external actions, successful JSON readback.
- `python -m pip check` reports no broken requirements.
- Gate A retains its exact V1 behavior. C2 does not claim per-tool permission enforcement for arbitrary IntentSpec inputs; that remains the explicitly unimplemented C3 Gate B boundary.
- Independent final certificate and shared push are still required before PASS.

### C2 final independent verification and shared handoff — 2026-09-08

- Independent verdict: **VERIFIED**, against the precommitted V1–V5 conditions and repaired implementation commit `302887dc2fd87e8e15148b3152cd5fc6030c08a8`.
- Independent evidence: `reports/c2/INDEPENDENT_VERIFICATION.md`. The verifier made no repository changes and did not build the implementation.
- Independent full suite: 82 passed in 49.17s. Independent frozen benchmark, using temporary output paths: 48/48 decisions, reasons, repeats, and intent linkage; macro-F1 1.000; zero unsafe approvals and external actions.
- Independent trace and assignment probes pass: six complete action/observation joins, all intent/run/plan links, contiguous event/state transitions, JSON readback, evidence-backed outcome, and no mutation after rejected linked-state updates.
- Final executor regression after the repair also passes: 82 tests and frozen benchmark 48/48, unchanged input hash.
- Documented install `python -m pip install -e ".[dev,runtime]"` successfully builds and installs with normal build isolation. An optional attempt without build isolation failed because the pre-existing environment lacked `bdist_wheel`; no build-system changes were needed.
- Shared handoff: the commit containing this finalized ledger and independent report is pushed to `v2-closure-execution`; its parent is the verified implementation checkpoint above. The exact shared SHA is recoverable from the branch and returned with completion.
- C2 is PASS only as this verified checkpoint is shared on GitHub. Stop here. C3/Gate B remains unauthorized; no merge to `main` is authorized or performed.

## C3 phase contract — committed before implementation

- SOURCE_SCOPE: new `src/control_gate/runtime_admissibility.py`; the existing tool-dispatch boundary in `src/control_gate/invoice_runtime.py`; existing RuntimeDecision/ExecutionRun contracts only if necessary; focused `tests/test_runtime_admissibility.py`; narrowly superseded C2 assertions in `tests/test_invoice_runtime.py`; this ledger and `reports/c3/`.
- Entry: clean local and live remote branch both at C2 shared checkpoint `96e8f4ad00ab925d0c47cd521a950afe612e3888`; live main remains `6c48d6449080b0e036025cb305b2c590b00737a4`. Notion sections 7/13 define frozen Gate B requirements. Its section 18 still shows C2; the user's newer explicit C3 authorization supersedes that stale execution-status text without changing the frozen architecture.
- D: every proposed tool action on the existing C2 trajectory is checked against immutable authorized intent/version/plan and current execution evidence before dispatch. Only an action's fresh APPROVE decision can reach its tool. Unauthorized actions must be observably blocked before tool invocation.
- ALLOWED: deterministic Gate B decisions using the existing public decision alphabet and RuntimeDecision; a single guarded dispatch boundary; stable runtime reason codes; action/decision/event linkage; adversarial tests with tool spies; local evidence; independent verification; bounded commit/push to `v2-closure-execution`.
- FORBIDDEN: changes to V1 compiler/validator/Gate A or C1 tools, frozen 48-case inputs, historical reports/C2 trace; new orchestration, dependencies, HITL interrupt/resume or approval resolution, retries/recovery/memory, service/deployment/CI, experiments, real external business effects, main merge, C4.
- V1: existing V1/C1 tests and frozen benchmark pass unchanged; preserve benchmark SHA-256 `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`. C2 happy-path tools, order, local outcome, identity, isolation, serialization, and terminal stop behavior remain covered.
- V2: all six C2 tool calls pass through one guard; each executed action has a preceding fresh APPROVE with matching run/intent/version/plan/action/arguments. Non-APPROVE has no tool-start event or tool invocation. No caller-supplied decision bypass.
- V3: deterministic tests cover goal/scope expansion, tool/actor/resource permissions, amount/currency/approved cap, prohibited operations, new unsafe assumptions, missing or contradictory required evidence, replay of a denied/failed action, repeated failed action, and non-clear human approval/override state. C3 reads and stops on these states; it does not implement retry or human continuation.
- V4: actual dispatched argument bytes are those evaluated and recorded, so proposal mutation or a stale decision cannot authorize a different call. Decision reason codes and all intent/run/action links serialize and remain stable.
- V5: focused adversarial integration tests prove zero calls with spies (not merely zero staging results), complete regression suite and benchmark pass, independent verifier returns VERIFIED, and shared checkpoint is pushed.
- Narrow verifier evolution: C2 assertions that explicitly required no RuntimeDecision/no Gate B events must now require Gate B evidence. Cases previously rejected inside C1 staging for inactive supplier/insufficient PO amount must now expect rejection before staging and zero staging calls. Preserve all other C2 assertions; have the independent verifier review this exact adaptation before treating it as a verification oracle.
- OUTPUT: implementation, focused tests, bounded approved/blocked trace evidence, independent verification report, and updated execution ledger on the shared branch.
- STOP: VERIFIED + PUSHED C3, or genuine trajectory-changing BLOCKER. C4 is not authorized.

### C3 implementation evidence — 2026-09-08

- Precommitted C3 contract and narrow verifier evolution: `86aa672`. Before the existing C2 assertions were edited, the independent verifier confirmed that the exact adaptation strengthens the same trajectory invariants at the newly authorized before-tool boundary.
- Entry regression: 82 passed in 38.71s; frozen benchmark PASS 48/48 with unchanged hash.
- Implementation: `src/control_gate/runtime_admissibility.py` plus the existing controller's single `_dispatch` boundary. Every one of the six C2 calls is frozen, freshly evaluated, recorded, and dispatched only on its matching APPROVE. There is no caller-supplied decision or ungated runtime option.
- Existing contracts and commodity scheduling are unchanged. Gate B reuses RuntimeDecision, TrajectoryEvent, the frozen finance policy, V1 actor/action vocabulary, and C1 record schemas. No dependency was added.
- Permission mapping: `inspect_invoice`, `check_duplicate`, and `retrieve_policy` are bounded invoice-validation operations under `invoice.parse`; supplier/PO lookup require `vendor.lookup`/`po.lookup`; local staging requires `payment.submit`. This explicit adapter preserves the V1 permission vocabulary.
- REJECT produces a terminal rejected outcome without dispatch. CLARIFY/ESCALATE stop in their existing states, retaining reasons and required state; C3 does not obtain information, resolve approvals, resume, or retry. Prior control stops, tool failures, pending questions, retry state, and non-clear human authority cannot silently resume execution.
- Reviewed implementation corrections: captured evaluated proposals are also used for event payloads, actual arguments, and current run.proposed_action; stale/current external proposal mutation cannot relabel an approval. Policy evidence uses matching JSON representations to avoid frozen tuple versus JSON list comparison errors.
- Focused integrated tests before the final three additions: 82 passed in 9.15s (56 new C3 cases plus 26 adapted C2 cases). Final full suite: `./.venv/Scripts/python.exe -m pytest -q --tb=short` → **141 passed in 32.73s** (56 unchanged V1/C1, 26 C2, 59 new C3 cases).
- Frozen benchmark: `./.venv/Scripts/python.exe -m control_gate benchmark` → PASS; 48/48 decisions, reason codes and deterministic repeats; macro-F1 1.000; zero unsafe approvals; zero external actions.
- Frozen input SHA-256: `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`.
- Proof packet: `reports/c3/gate_b_proof.json`, SHA-256 `61dd150fbfe910008a83c5ccff52a3d4807eb48b64954715bcbad180937b0b2f`. Approved trajectory: six real calls, 22 linked events, one local stage. Seven injected end-to-end violations: five permitted reads each, zero unauthorized/staging calls, zero staged payments, and a recorded non-APPROVE before dispatch. This is bounded acceptance evidence, not the C7 experiment.
- `git diff --exit-code 96e8f4a` over V1 compiler/validator/Gate A, existing contracts, C1 tools, benchmark inputs, historical outputs/reports, C2 trace, and dependency manifest is clean. Existing C2 test changes match only the independently reviewed evolution. `git diff --check` passes.
- Independent final certificate, implementation checkpoint, and shared push remain pending. C4 is unauthorized.

### C3 final independent verification and shared handoff — 2026-09-08

- Independent verdict: **VERIFIED** against precommitted C3 V1–V5 and implementation commit `6ef6f96b88650a192241b85c1148cf4a6142ac9d`.
- Independent report: `reports/c3/INDEPENDENT_VERIFICATION.md`. The separate verifier made no implementation or test edits.
- Independent full suite: **141 passed in 35.75s**. Independent frozen benchmark used temporary output paths: 48/48 decision, reason, repeat, and intent-linkage matches; macro-F1 1.000; zero unsafe approvals and external actions.
- Independent adversarial probes confirmed zero staging calls for altered scope, actor, tool, amount, currency, resource, assumptions, human authority, and retry state. Additional coherent evidence substitutions were rejected before any spy call.
- The saved C3 proof packet contains the approved linked trajectory and seven blocked end-to-end proposals, with actual tool-call observations and unchanged hash `61dd150fbfe910008a83c5ccff52a3d4807eb48b64954715bcbad180937b0b2f`.
- Shared checkpoint: the documentation-only commit containing this final ledger/report, whose parent is the verified implementation commit, is pushed to `v2-closure-execution`. Its exact SHA is returned with completion and recoverable from the branch.
- C3 is PASS as this verified checkpoint is shared on GitHub. Stop here. C4 is not authorized; no main merge, HITL, recovery, service/deployment, or experiment work is included.
