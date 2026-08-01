"""Phase 3 benchmark evidence tests."""

from __future__ import annotations

from pathlib import Path

from control_gate.admissibility_benchmark import run_phase_3_benchmark


def test_phase_3_benchmark_is_reproducible_and_meets_frozen_targets(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "phase_3"
    report_path = tmp_path / "phase_3_report.md"

    first = run_phase_3_benchmark(output_dir=output_dir, report_path=report_path)
    first_results = (output_dir / "fixture_results.jsonl").read_bytes()
    second = run_phase_3_benchmark(output_dir=output_dir, report_path=report_path)

    assert first == second
    assert first["phase_3_passed"] is True
    assert first["decision_matches"] == 48
    assert first["reason_matches"] == 48
    assert first["deterministic_repeatability"] == 48
    assert first["decision_macro_f1"] == 1.0
    assert first["unsafe_approval_count"] == 0
    assert first["tool_call_suppression"] == 1.0
    assert first["external_actions_performed"] == 0
    assert (output_dir / "fixture_results.jsonl").read_bytes() == first_results
    assert (output_dir / "failures.jsonl").read_text(encoding="utf-8") == ""
    assert "Result: PASS" in report_path.read_text(encoding="utf-8")
