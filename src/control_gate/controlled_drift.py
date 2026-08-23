"""Controlled/synthetic drift testing layer."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Sequence

from control_gate.admissibility import decide
from control_gate.compiler import FixtureCompiler, RequestFixture
from control_gate.contracts import Decision


@dataclass
class DriftBatch:
    name: str
    fixtures: list[RequestFixture]


@dataclass
class DriftReport:
    batch_name: str
    case_count: int
    baseline_decision_distribution: dict[str, int]
    drifted_decision_distribution: dict[str, int]
    baseline_reason_distribution: dict[str, int]
    drifted_reason_distribution: dict[str, int]
    unexpected_regressions: list[str]


def _update_fixture_context(fixture: RequestFixture, **updates) -> RequestFixture:
    payload = fixture.model_dump(mode="python")
    payload["context"].update(updates)
    return RequestFixture.model_validate(payload)


def generate_drift_batches(base_fixtures: Sequence[RequestFixture]) -> list[DriftBatch]:
    """Create deterministic shifted batches changing justified input distributions."""

    # Batch 1: Inflation drift (multiply existing amounts by 10)
    inflation_fixtures = []
    for f in base_fixtures:
        new_amount = f.context.amount
        if new_amount:
            try:
                val = Decimal(new_amount)
                new_amount = str(val * 10)
            except InvalidOperation:
                pass
        inflation_fixtures.append(_update_fixture_context(f, amount=new_amount))

    # Batch 2: Vendor attrition drift (vendors suddenly disappear)
    vendor_fixtures = []
    for f in base_fixtures:
        vendor_fixtures.append(_update_fixture_context(f, supplier_exists=False))

    return [
        DriftBatch("inflation_drift", inflation_fixtures),
        DriftBatch("vendor_attrition_drift", vendor_fixtures),
    ]


def measure_drift(
    baseline_fixtures: Sequence[RequestFixture],
    batch: DriftBatch
) -> DriftReport:
    compiler = FixtureCompiler()

    baseline_decisions = []
    baseline_reasons = []
    drifted_decisions = []
    drifted_reasons = []
    regressions = []

    for base, drifted in zip(baseline_fixtures, batch.fixtures, strict=True):
        base_intent = compiler.compile(base)
        base_res = decide(base_intent)
        baseline_decisions.append(base_res.decision.value)
        baseline_reasons.extend(base_res.reason_codes)

        drift_intent = compiler.compile(drifted)
        drift_res = decide(drift_intent)
        drifted_decisions.append(drift_res.decision.value)
        drifted_reasons.extend(drift_res.reason_codes)

        # Check unexpected regressions
        if batch.name == "inflation_drift":
            # REJECT/CLARIFY should not turn into APPROVE
            if base_res.decision in {Decision.REJECT, Decision.CLARIFY} and drift_res.decision == Decision.APPROVE:
                regressions.append(f"{base.fixture_id}: unexpected APPROVE in inflation drift")

        elif batch.name == "vendor_attrition_drift":
            # Nothing should be APPROVED if vendor doesn't exist (unless CLARIFY blocks it first, but APPROVE is never right)
            if drift_res.decision == Decision.APPROVE:
                regressions.append(f"{base.fixture_id}: unexpected APPROVE in vendor attrition drift")

    return DriftReport(
        batch_name=batch.name,
        case_count=len(batch.fixtures),
        baseline_decision_distribution=dict(Counter(baseline_decisions)),
        drifted_decision_distribution=dict(Counter(drifted_decisions)),
        baseline_reason_distribution=dict(Counter(baseline_reasons)),
        drifted_reason_distribution=dict(Counter(drifted_reasons)),
        unexpected_regressions=regressions
    )
