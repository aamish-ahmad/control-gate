# C7 independent verification certificate

Date: 2026-09-10 (Asia/Kolkata)
Verifier: Codex independent verifier (GPT-5 class; model-tier attestation is not persisted in the repository)
Candidate commit: `9d81162abce9561c75f2e1e987e4db317520d4de`
Precommitted C7 contract: `8ae1b5d5175ef4e34734b83537770af94628bcf0`

## Verdict

**VERIFIED**

All C7 V1-V5 conditions passed against the immutable candidate snapshot. The local remote-tracking ref `origin/v2-closure-execution` resolves exactly to the candidate, and the supplied remote readback confirms the pushed branch also resolves to `9d81162abce9561c75f2e1e987e4db317520d4de`.

## Snapshot and scope

- `git rev-parse HEAD` returned `9d81162abce9561c75f2e1e987e4db317520d4de`.
- `git rev-parse refs/remotes/origin/v2-closure-execution` returned the same SHA; direct `git ls-remote` was temporarily unavailable in this shell, so the final remote readback is bound to the recorded successful readback supplied for this candidate.
- `git status --short` was clean before and after verification except for this intentionally uncommitted certificate.
- The final candidate diff from the precommitted contract contains only authorized C7 surfaces plus the bounded installed-package resolution/test-portability repair in `src/control_gate/agent_benchmark.py` and `tests/test_agent_benchmark.py`; no frozen experiment outputs or metrics changed.
- No C7 experiment command was invoked; no episode was rerun, and no latency was remeasured. The canonical no-flag `python -m control_gate.agent_benchmark` command was not invoked.
- The verifier wrote only this certificate; it did not stage, commit, push, or edit the ledger.

## V1: regression and protected evidence

Commands and results:

```text
./.venv/Scripts/python.exe -m pytest -q --tb=short
254 passed, 1 warning in 60.10s

./.venv/Scripts/python.exe -m control_gate benchmark
PASS; 48 fixtures; 48 decision matches; 48 reason-code matches;
48 deterministic repeats; macro-F1 1.000; unsafe approvals 0; external actions 0

./.venv/Scripts/python.exe -m pip check
No broken requirements found.

./.venv/Scripts/python.exe -m compileall -q src tests
PASS
```

Matplotlib availability was independently checked: `matplotlib 3.11.1`, `numpy 2.4.6`; pandas was absent and was not needed. The interrupted-install concern is therefore clear for the required plotting library.

Protected/frozen SHA-256 values observed:

```text
benchmarks/requests.jsonl                         4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503
reports/c2/supplier_invoice_trajectory.json      c03230b0fbf7e8e1b25292219c89ee09133a2cad228c160b1852d06a54718083
reports/c2/INDEPENDENT_VERIFICATION.md           36581ba53d06dfaa7c437a6154406090f1b89b91dec51bb3615f038a7ddcdcbc
reports/c3/gate_b_proof.json                     61dd150fbfe910008a83c5ccff52a3d4807eb48b64954715bcbad180937b0b2f
reports/c3/INDEPENDENT_VERIFICATION.md           4bb1ba998cc6a049c383d2285b9d967c053cf0b5df6b14030bc5df7dde03a9ed
reports/c4/human_control_proof.json              fc279503808d8946825b463bef5ca7efbb66a65afde32b4195333c6fc9241d60
reports/c4/INDEPENDENT_VERIFICATION.md           4aaba5f1136d66b2766c74db62d8f9f53e8dbf0d52914fcb416bda7ca19ce49e
reports/c5/recovery_proof.json                   de1a67a47fefc5918d76b16869ba409bafebf4830cfe6d5efab308d75e65f1d2
reports/c5/INDEPENDENT_VERIFICATION.md           0d4023e6dcb688fbd21df7c95204001cfb190b7ffe2e63c2e08149febf06472e
reports/c6/engineering_proof.json                378412fc7ebad4956cb97429fb67a6df081f9137319de567e951d0736d32ab0c
reports/c6/INDEPENDENT_VERIFICATION.md           9bfdd085f64660d09414c00752de6bf5a5ca24c8f3f21aaa24885699538b83f3
```

These protected hashes were unchanged after verification. No protected source/test/benchmark/evidence path appeared in the C7 candidate diff.

## V2: frozen task set and episode pairing

Independent `load_tasks`, `task_digests`, and raw-episode checks returned:

- 50 tasks, with exactly: straightforward admissible 10; underspecified 6; approval-required 6; prohibited 5; contradictory evidence 5; tool failures 5; retry/recovery 5; runtime scope expansion 4; human override/intervention 4.
- 100 raw episode rows: 50 `GATED` and 50 `UNGATED`; all 50 task IDs have exactly one row per arm.
- Alternating pair order is balanced (25 pairs GATED first, 25 UNGATED first).
- Every paired task has identical task/request/environment/failure/human/proposal-mutation digests across arms.
- No hidden exclusions and zero external actions in both arms.

Raw evidence SHA-256:

```text
benchmarks/agent_tasks.jsonl  c69c891dce03f111684f5237fbd94a6e3352e7685da1c1a82737b1062f6e5276
outputs/c7/episodes.jsonl     771e7ad35648436bf20e62082283f983d5d2d1300b5e74743882c536974940f3
outputs/c7/summary.json       f353bd2a7d9006587e705aaecf130a1ce9d320c660149caeb4ae3e69d416a7c
```

## V3/V4: runtime, metrics, statistics, and chart determinism

The focused C7 suite passed independently:

```text
./.venv/Scripts/python.exe -m pytest -q tests/test_agent_benchmark.py --tb=short
14 passed in 10.93s
```

Independent raw recomputation produced byte-identical `comparison.csv` (SHA-256 `88edd4fad867bcf55785f50b8bcc4113ba1c37b168357bd940fa1ed48d87ffa6`) and summary metric sections identical to `summary.json`. Recomputed primary results include:

- Task success: GATED 50/50 = 100%; UNGATED 23/50 = 46%; paired difference +54 percentage points; discordance 27/0; exact two-sided p = `1.4901161193847656e-08`.
- Unsafe action: GATED 0/50 = 0%; UNGATED 23/50 = 46%; paired difference -46 points; discordance 0/23; exact two-sided p = `2.384185791015625e-07`.
- Runtime contract violation: GATED 0/50 = 0%; UNGATED 22/50 = 44%; paired difference -44 points; discordance 0/22; exact two-sided p = `4.76837158203125e-07`.
- Mean latency: GATED `188.0072 ms`; UNGATED `241.945576 ms`; paired mean GATED-minus-UNGATED `-53.938376 ms` (`-22.2936%`).

Chart-only determinism was tested twice from the frozen comparison CSV using `regenerate_chart_only` into isolated temporary outputs. Both runs matched exactly:

```text
PNG  0299a05c9047155d70f801ee07a6e0d3fda7ab5006f3a31fec0c5db8e6c38f36
SVG  396b9ba8dc641b547625b17dbf1873b19e7e23ef43ab9f6558337437b6126331
PDF  abe45c48b2bc9383ce130d93a735f077e4f84d8513724b8b42906c6b6be1a61b
```

The frozen `summary.json` SHA-256 remained `f353bd2a7d9006587e705aaeacf130a1ce9d320c660149caeb4ae3e69d416a7c`; episodes, comparison, and RESULTS were not modified. The rendered PNG was visually inspected at its native 2800x1700 size: normal fonts, no clipping, obvious GATED/UNGATED comparison, task-success and safety gains immediately legible, and latency/tool-call overhead visible in the right panel. The chart implementation reads only the frozen comparison CSV and uses installed Matplotlib; no hand-built glyphs or bitmap renderer are present.

## V5: scope and closure checks

- Focused C7, complete suite, frozen 48-case benchmark, compile, and pip checks passed as above.
- GitHub Actions run [34499135146](https://github.com/aamish-ahmad/control-gate/actions/runs/34499135146) completed successfully, covering non-editable dependency installation, the 254-test suite, the frozen benchmark, and Docker build. Earlier runs `34493396397` and `34495832216` were bounded failures diagnosed as cross-platform PNG-test portability and installed-wheel project-root resolution; the final repair is limited to those concerns. Linux WSL non-editable installation independently passed all 254 tests.
- Zero external actions were observed; this deterministic runtime makes no model calls and does not estimate LLM token/cost overhead.
- No C8 source/report surface exists in the worktree. The only `c8` filename matches were internal Git object names or an unrelated OpenBLAS DLL, not repository C8 content.
- The local candidate snapshot remained unchanged throughout verification.
- The pushed `v2-closure-execution` branch readback matches the candidate SHA `9d81162abce9561c75f2e1e987e4db317520d4de`; no merge to `main` occurred.

## Certificate integrity

This file is intentionally uncommitted per the verifier assignment. No experiment rerun, C8 action, chart data change, metric change, or ledger update was performed.
