# C2 independent verification

Verdict: **VERIFIED**

Date: 2026-09-08

Precommitted conditions: `docs/V2_EXECUTION_STATE.md`, V1–V5, committed at `5386009` before implementation.

Verified implementation: `302887dc2fd87e8e15148b3152cd5fc6030c08a8`.

Verification was performed by a separate read-only verifier using the global `independent-verifier` skill. The verifier did not edit source, tests, artifacts, or Git state. This report records its returned observations and final certificate.

## Independent observations

- Full test suite: **82 passed in 49.17s**. The original 56 V1/C1 tests remain unchanged; the 26 focused C2 cases supplement them.
- The unchanged `run_phase_3_benchmark` was independently executed with temporary output paths. Results: 48/48 decision matches, 48/48 reason-code matches, 48/48 deterministic repeats, 48/48 intent linkage, macro-F1 1.000, zero unsafe approvals, zero external actions.
- Frozen `benchmarks/requests.jsonl` SHA-256: `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`.
- The candidate diff is bounded to the ledger, runtime dependency, additive contract state, one invoice runtime module, new focused tests, and C2 trace. Existing Gate A/compiler/validator/C1 tools, existing tests, benchmark inputs, and historical evidence are unchanged.
- Gate A non-APPROVE paths invoke no tools. APPROVE reaches the actual C1 fixture environment and local staging. Observed missing, duplicate, inconsistent, or inactive records terminate safely without retry or external action.
- Serialized trace roundtrip passes. All run/intent/version links, plan links, action joins, contiguous event sequence numbers, and state edges are consistent. The six started/completed/observation joins agree with accumulated evidence and the terminal outcome.
- Final trace: `reports/c2/supplier_invoice_trajectory.json`; SHA-256 `c03230b0fbf7e8e1b25292219c89ee09133a2cad228c160b1852d06a54718083`; six tools, 16 events, one local staged payment, zero external actions.
- Independent bad-event, bad-outcome, and bad-runtime-decision assignments reject and preserve the entire serialized trajectory unchanged.

## Review finding and bounded correction

The first implementation used an after-model validator for linked state. The verifier reproduced a rejected event assignment that still left the mismatched event in the run. The builder moved validation to the fields before mutation and added three regression cases. Independent probes confirmed the correction at the verified implementation checkpoint.

## Scope of the certificate

This certificate covers C2 only: a deterministic, stateful local supplier-invoice controller, existing Gate A entry, real C1 tools, linked state/evidence, and a supported local outcome. `RuntimeDecision` is an unused C3 contract interface and remains null during execution.

V1 Gate A permissiveness is unchanged. This certificate does not claim that arbitrary IntentSpec permissions are enforced per tool; that is C3 Gate B work. Human continuation, retries/recovery, persistence services, deployment, and experiments remain outside this checkpoint.

The final independent response was: `VERIFIED`.
