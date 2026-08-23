"""Tests for the differential testing layer."""

from __future__ import annotations

from control_gate.benchmark import load_fixtures
from control_gate.differential import run_differential_evaluation


def test_differential_back_to_back() -> None:
    # Use the frozen benchmark as the explicit reference behavior
    fixtures = load_fixtures()
    report = run_differential_evaluation(fixtures)

    print(f"\nDifferential Evaluation on {report.total_cases} frozen cases:")
    print(f"- Decision agreement: {report.decision_agreement}/{report.total_cases}")
    print(f"- Reason-code agreement: {report.reason_code_agreement}/{report.total_cases}")
    print(f"- Changed cases: {len(report.changed_cases)}")
    print(f"- Unsafe regressions: {len(report.unsafe_regressions)}")

    assert report.decision_agreement == report.total_cases, f"Decision mismatch in {len(report.changed_cases)} cases"
    assert report.reason_code_agreement == report.total_cases, f"Reason code mismatch in {len(report.changed_cases)} cases"
    assert len(report.unsafe_regressions) == 0, f"Found {len(report.unsafe_regressions)} unsafe regressions!"
