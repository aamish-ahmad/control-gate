# C4 independent verification

Verdict: **VERIFIED**

Date: 2026-09-09

Precommitted contract: `f817f21`, C4 V1–V5 in `docs/V2_EXECUTION_STATE.md`.

Verified implementation: `3853d8b49817d0eebc9b96d3b47c01b718d861f9`.

A separate read-only verifier applied the global independent-verifier skill. It made no repository edits. This report records its returned observations and final certificate. All six source/test blob hashes matched the independently tested versions at the clean candidate checkpoint.

## Independent evidence

- Full suite: **205 passed in 10.20s**. Focused C4 suite: **64 passed in 4.83s**. All 141 prior tests remain unchanged.
- Frozen benchmark, using temporary output paths: 48/48 decisions, reasons, repeats and intent links; macro-F1 1.000; zero unsafe approvals and external actions.
- V1 gate code, dependencies, frozen benchmark inputs and prior evidence artifacts remained unchanged.
- Malformed, stale, wrong-role, no-op, widening, copied, serialized and replayed interventions are rejected before new tool calls. Accepted interventions consume the parent before child dispatch, preserve frozen parent identity and contract, and link a new intent version and plan.
- Independent late-state probes changed the retained environment to duplicate invoice, inactive supplier, closed PO or incomplete validation after escalation. Explicit manager approval still led to FAILED/REJECTED after four or five permitted reads, with zero staging calls and records.
- Review identified malformed clarification values, semantic no-ops and ineffective prohibition additions. These were repaired within the precommitted C4 scope and covered by new C4 tests. No prior test was weakened or edited.
- The exact immutable human approval is included in Gate B and tool-start event metadata and matches the authority actually passed to C1 staging.

## Saved trajectory proof

File: `reports/c4/human_control_proof.json`

SHA-256: `fc279503808d8946825b463bef5ca7efbb66a65afde32b4195333c6fc9241d60`

The verifier checked nine cases: two completed and seven blocked/cancelled. Six consumed-parent replay attempts added zero calls. Parent identities/contracts, child links and intent-version increments, human actors, approval context, JSON readback, event/state sequences and evaluated/recorded/dispatched arguments matched. Each completed case staged one local payment after six guarded calls; blocked cases performed no staging.

## Scope and handoff

This is a bounded local trusted-human API with single-use live pause handles. It does not claim external identity authentication, persistent recovery, service/deployment or experiment results. Gate A remains unchanged; human approval never bypasses current evidence, resource, permission, prohibition or business validation checks. No external business action occurred.

The implementation satisfies C4 V1–V5. The executor must record this certificate and push the final bounded checkpoint before reporting shared C4 completion. C5 remains unauthorized.
