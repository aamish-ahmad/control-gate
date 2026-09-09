# C6 Independent Verification

Verdict: **VERIFIED**

The immutable implementation candidate `8e16b498656a24d18e8fc055a35d42a211b8d480` is exactly the child of the precommitted C6 contract checkpoint `76de5505124a9084b2965ed3937fd8a269e3af75`. The verifier inspected the candidate diff and Git blobs independently and made no implementation, test, proof, ledger, dependency, Docker, or CI changes.

## Evidence

- Focused command: `.\.venv\Scripts\python.exe -m pytest -q tests/test_persistence.py tests/test_service.py --tb=short` -> **11 passed**.
- Complete command: `.\.venv\Scripts\python.exe -m pytest -q --tb=short` -> **240 passed** (one existing Starlette deprecation warning).
- Frozen benchmark: `.\.venv\Scripts\python.exe -m control_gate benchmark` -> **PASS**, 48/48 decisions, 48/48 reason codes, 48/48 deterministic repeats, macro-F1 1.000, zero unsafe approvals, zero external actions.
- Proof builder/readback: `.\.venv\Scripts\python.exe reports\c6\build_proof.py` produced a valid C6 proof showing 22 contiguous events, one run row, 22 event rows, SQLite integrity `ok`, restart and event readback equality, and zero external actions. The committed proof blob SHA-256 is `378412fc7ebad4956cb97429fb67a6df081f9137319de567e951d0736d32ab0c`.
- Python compile/import and dependency checks pass: `python -m compileall -q src tests reports\c6\build_proof.py`; `python -m pip check` -> `No broken requirements found`.
- Protected hashes match the C6 contract: frozen benchmark `4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503`; C2 trace `c03230b0fbf7e8e1b25292219c89ee09133a2cad228c160b1852d06a54718083`; C2 certificate `36581ba53d06dfaa7c437a6154406090f1b89b91dec51bb3615f038a7ddcdcbc`; C3 certificate `4bb1ba998cc6a049c383d2285b9d967c053cf0b5df6b14030bc5df7dde03a9ed`; C4 proof `fc279503808d8946825b463bef5ca7efbb66a65afde32b4195333c6fc9241d60`; C4 certificate `4aaba5f1136d66b2766c74db62d8f9f53e8dbf0d52914fcb416bda7ca19ce49e`; C5 proof `de1a67a47fefc5918d76b16869ba409bafebf4830cfe6d5efab308d75e65f1d2`; C5 certificate `0d4023e6dcb688fbd21df7c95204001cfb190b7ffe2e63c2e08149febf06472e`.

## Contract review

The SQLite store validates serialized `ExecutionRun` and `TrajectoryEvent` contracts, requires unique contiguous sequence numbers, writes runs and events transactionally, performs exact-repeat idempotence, and rejects changed content, index/payload divergence, event-count/order mismatch, invalid payloads, and corrupted event rows. The service is a thin create/get/events/health boundary over the unchanged `execute_invoice` path; malformed input and unknown runs fail closed. OpenAPI exposes no resume endpoint or authorization bypass. Adversarial focused tests cover idempotence, corruption, ordered events, restart readback, malformed requests, 404s, and zero external actions.

Static review confirms SQLite path configuration through `CONTROL_GATE_DB_PATH`, a non-root `controlgate` container user, persistent `/data` volume, and CI steps for installation, full tests, frozen benchmark, and Docker build. Docker is not installed locally, so no local build claim is made. Parent-observed public GitHub Actions evidence at [run 34405797475](https://github.com/aamish-ahmad/control-gate/actions/runs/34405797475) reports success for install, pytest, benchmark, and `docker build --tag control-gate:c6 .`.

Protected implementation semantics, V1-C5 tests/evidence, benchmark inputs, and README are unchanged in the candidate diff. No C7 work is included.
