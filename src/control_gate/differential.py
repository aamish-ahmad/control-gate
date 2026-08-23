"""Differential/back-to-back testing layer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from control_gate.admissibility import decide
from control_gate.compiler import FixtureCompiler, RequestFixture
from control_gate.contracts import Decision


@dataclass
class DifferentialReport:
    total_cases: int
    decision_agreement: int
    reason_code_agreement: int
    changed_cases: list[str]
    unsafe_regressions: list[str]


def run_differential_evaluation(fixtures: Sequence[RequestFixture]) -> DifferentialReport:
    """Compare current runtime evaluation against the frozen expected behavior."""
    compiler = FixtureCompiler()

    total = len(fixtures)
    decision_agreement = 0
    reason_code_agreement = 0
    changed_cases = []
    unsafe_regressions = []

    for fixture in fixtures:
        intent = compiler.compile(fixture)
        result = decide(intent)

        decision_match = result.decision == fixture.expected_decision
        reason_match = set(result.reason_codes) == set(fixture.expected_reason_codes)

        if decision_match:
            decision_agreement += 1
        if reason_match:
            reason_code_agreement += 1

        if not decision_match or not reason_match:
            changed_cases.append(fixture.fixture_id)

        # An unsafe regression is when the reference expects ESCALATE/REJECT on a critical policy,
        # but the current system APPROVES it.
        if fixture.critical_policy and fixture.expected_decision in {Decision.ESCALATE, Decision.REJECT}:
            if result.decision == Decision.APPROVE:
                unsafe_regressions.append(fixture.fixture_id)

    return DifferentialReport(
        total_cases=total,
        decision_agreement=decision_agreement,
        reason_code_agreement=reason_code_agreement,
        changed_cases=changed_cases,
        unsafe_regressions=unsafe_regressions,
    )
