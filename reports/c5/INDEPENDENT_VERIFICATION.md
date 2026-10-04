# C5 Independent Verification

Verdict: **VERIFIED**

## Verification binding

- Project and branch: Control Gate, `v2-closure-execution`.
- Precommitted C5 contract: `e04e9954fad1b99e3110e1ac13a96ec9b38881dd`.
- Independently tested implementation commit: `51e7b6ef30d85380204ea224592f076e5cd57ab0`.
- Candidate parent: exactly the precommitted contract above.
- Canonical contract checked against live Notion page `3c0d086d-0fe9-81ec-9e0f-c28b316836e1`, **04 — Control Gate V2 — Closure Spec**, fetched 2026-09-09. Its C5 recovery/failure matrix and C5 authorization agree with the precommitted repository V1–V5 conditions. The older section-18 C2 status is historical and does not override the page's newer C5 authorization or the user's explicit C5 instruction.

Candidate Git blobs tested:

- `src/control_gate/invoice_runtime.py`: `ed58ae5c9ea184cc1700a787fed113ba48707c28`
- `src/control_gate/runtime_admissibility.py`: `3144e05f5d0fe43947ce6586bca0c5bdc449510a`
- `src/control_gate/tool_environment.py`: `e06d636d1e26eaff2602574ed2d95fe557d5e697`
- `tests/test_recovery.py`: `0d9f2224ca9666d83258d8214882a9592bead1dc`
- `reports/c5/build_proof.py`: `7ef05d9569947cab538fa976976a8362d2622c99`
- `reports/c5/recovery_proof.json`: `e6c05e324b78515dfabd2b6db3f3055b56154fa6`
- `docs/V2_EXECUTION_STATE.md`: `0bec85c7ca49d08760dcef3b4f4b366cd18cdf1e`

## Independent evidence

- `python -B -m pytest -q tests/test_recovery.py --tb=short -p no:cacheprovider` using the repository virtual environment: **24 passed in 4.04s**.
- `python -B -m pytest -q --tb=short -p no:cacheprovider`: **229 passed in 14.68s**.
- Independently redirected `run_phase_3_benchmark` in a temporary output directory: **PASS**, 48/48 decision matches, 48/48 reason matches, 48/48 deterministic repeats, intent linkage 48/48, macro-F1 1.000, zero unsafe approvals, and zero external actions.
- Independent in-memory adversarial probes accepted a valid retry boundary, rejected missing failure events, missing retry events, a cross-run failed-action ID, a forged/exhausted retry counter, a changed retry resource, a prior Gate B REJECT, and a terminal run. An unclassified native timeout failed closed with zero retries and zero staging.
- Independent maximum-cap recovery injected two timeouts into each of the five read-only steps. The run completed with 16 linked attempts, 10 retry events, exactly one completion for each of the six fixed tools, one local staged record, a single run/intent/version episode, and exact `ExecutionRun` JSON round-trip.
- Source review confirms every retry attempt returns through `_dispatch` and receives a fresh `decide_runtime` Gate B decision before any tool start. Retry lineage is joined across policy-check, start, failed observation, retry-scheduled, and next-action records. The fixed action proposal is re-evaluated, completed evidence is retained, malformed output is excluded from evidence, and successfully completed tools are not replayed.
- Only explicitly classified `TOOL_TIMEOUT` and `MALFORMED_TOOL_RESPONSE` failures on the five read-only steps may retry, capped by the existing `finance-v1` value of two. `stage_payment` has zero retries. Permission denial, missing records, contradictions, duplicates, unexpected failures, exhaustion, all staging failures, Gate B non-APPROVE, human deny/cancel/unresolved authority, and terminal state stop without staging or implicit authority.
- The saved proof read back as 10 terminal cases: two recovered completions and eight safe stops. It records zero external actions globally and per case. SHA-256: `de1a67a47fefc5918d76b16869ba409bafebf4830cfe6d5efab308d75e65f1d2`.

## Protected surfaces and scope

- `git diff --check e04e9954fad1b99e3110e1ac13a96ec9b38881dd..51e7b6ef30d85380204ea224592f076e5cd57ab0` passed.
- The candidate changes only the seven C5-authorized paths listed by `git diff --name-only`. Existing C0–C4 tests and evidence, V1 compiler/validator/Gate A surfaces, dependencies, benchmark inputs, README, service/deployment/CI surfaces, and packaging are unedited. The added C5 tests supplement rather than replace any pre-existing oracle, so the verifier remains valid.
- Frozen benchmark input SHA-256 remains `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503` (Git blob `710ba799947ac77080db3b0b2e1b423c410f69ce`).
- Protected evidence SHA-256 values remain: C2 trace `c03230b0fbf7e8e1b25292219c89ee09133a2cad228c160b1852d06a54718083`; C2 certificate `36581ba53d06dfaa7c437a6154406090f1b89b91dec51bb3615f038a7ddcdcbc`; C3 proof `61dd150fbfe910008a83c5ccff52a3d4807eb48b64954715bcbad180937b0b2f`; C3 certificate `4bb1ba998cc6a049c383d2285b9d967c053cf0b5df6b14030bc5df7dde03a9ed`; C4 proof `fc279503808d8946825b463bef5ca7efbb66a65afde32b4195333c6fc9241d60`; C4 certificate `4aaba5f1136d66b2766c74db62d8f9f53e8dbf0d52914fcb416bda7ca19ce49e`.
- No RetrievalOps/RAG integration, persistence, new framework/dependency, FastAPI, Docker, CI, service, experiment, external business effect, main merge, or C6 work is present.

The implementation satisfies the precommitted C5 V1–V5 verification conditions. This certificate does not authorize C6. The controller/executor must incorporate this report into the shared C5 checkpoint and push/read back that exact checkpoint before reporting C5 as pushed.
