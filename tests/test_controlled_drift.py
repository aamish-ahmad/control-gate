"""Tests for the controlled/synthetic drift testing layer."""

from __future__ import annotations

import json

from control_gate.benchmark import load_fixtures
from control_gate.controlled_drift import generate_drift_batches, measure_drift


def test_controlled_synthetic_drift() -> None:
    fixtures = load_fixtures()
    batches = generate_drift_batches(fixtures)

    assert len(batches) == 2, "Expected exactly 2 drift batches"

    for batch in batches:
        report = measure_drift(fixtures, batch)

        print(f"\nDrift Batch: {report.batch_name} ({report.case_count} cases)")
        print(f"Decision Shift: {json.dumps(report.baseline_decision_distribution, sort_keys=True)} -> {json.dumps(report.drifted_decision_distribution, sort_keys=True)}")
        print(f"Reason Shift (Top 3 baseline): {list(report.baseline_reason_distribution.items())[:3]}")
        print(f"Reason Shift (Top 3 drifted): {list(report.drifted_reason_distribution.items())[:3]}")
        print(f"Unexpected Regressions: {len(report.unexpected_regressions)}")

        assert len(report.unexpected_regressions) == 0, f"Found unexpected regressions in {report.batch_name}: {report.unexpected_regressions}"
