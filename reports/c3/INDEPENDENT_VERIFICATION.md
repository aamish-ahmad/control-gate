# C3 independent verification

Verdict: **VERIFIED**

Date: 2026-09-08

Precommitted contract: `86aa672`, C3 V1–V5 in `docs/V2_EXECUTION_STATE.md`.

Verified implementation: `6ef6f96b88650a192241b85c1148cf4a6142ac9d`.

A separate read-only verifier applied the global `independent-verifier` skill. It made no source, test, artifact, or Git changes. This report records its returned observations and final certificate.

## Independent evidence

- Full suite: **141 passed in 35.75s**. This comprises 56 unchanged V1/C1 tests, 26 C2 tests with the independently reviewed C3 assertion changes, and 59 new C3 tests.
- The unchanged frozen benchmark ran independently with temporary output paths: 48/48 decision matches, reason-code matches, deterministic repeats, and intent linkage; macro-F1 1.000; zero unsafe approvals and external actions.
- Frozen input SHA-256: `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`.
- Independent live integration probes changed scope, actor, prohibited tool, amount, currency, resource, assumptions, supplied human authority, and retry state immediately before staging. All nine produced non-APPROVE with zero `stage_payment` spy calls and records.
- Additional probes changed evidence consistently across accumulated evidence, observations, and completed events. Cross-resource supplier/PO contradictions, duplicate status, widened observed policy, and incomplete invoice validations were rejected before any spy call.
- Source review confirmed that all six top-level C1 calls pass through one guard. Every actual call uses a frozen proposal and a fresh RuntimeDecision; no caller-supplied decision or ungated execution switch exists.
- The evaluated snapshot is used for dispatched arguments, event metadata, and current proposed_action. Existing approval state cannot be reused to authorize modified arguments. Completed runs cannot dispatch again.
- V1 compiler/validator/Gate A, existing contracts, C1 tools, frozen inputs, historical evidence including C2, and dependencies are unchanged.

## Independently reviewed verifier evolution

Before the existing C2 test changes, the verifier approved the narrow adaptation committed in `86aa672`: assertions of absent Gate B became per-action fresh-APPROVE evidence checks; inactive-supplier/insufficient-PO cases moved from stage-time failure to Gate B rejection with zero staging calls. All other C2 behavior assertions remain.

The verifier identified two routine implementation details during review: normalize frozen policy evidence before JSON comparison, and retain the evaluated proposal for both events and current state when its mutable source is replaced. Both were corrected before the verified checkpoint.

## Shared proof packet

`reports/c3/gate_b_proof.json`

SHA-256: `61dd150fbfe910008a83c5ccff52a3d4807eb48b64954715bcbad180937b0b2f`.

- Approved case: six actual local tool calls, 22 linked events, one local staged payment, zero external actions, successful JSON readback.
- Seven end-to-end adversarial cases: each performs five permitted reads, then stops on non-APPROVE with zero unauthorized/staging calls and zero staged payments. The packet records actual call observations and events at the stop boundary.

This is bounded acceptance evidence, not the deferred C7 experiment. C3 only checks and stops on clarification, human-authority, and retry state. It does not implement information acquisition, human approval resolution/resume, recovery, services, or deployment.

The final independent response bound to the implementation checkpoint was: `VERIFIED`.
