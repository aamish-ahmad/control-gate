"""Phase 3 deterministic admissibility acceptance tests."""

from __future__ import annotations

from control_gate.admissibility import ReasonCode, decide
from control_gate.compiler import FixtureCompiler
from control_gate.contracts import Decision
from control_gate.fixtures import build_frozen_request_benchmark


def test_all_48_fixture_decisions_and_reason_codes_match() -> None:
    compiler = FixtureCompiler()

    for fixture in build_frozen_request_benchmark():
        intent = compiler.compile(fixture)
        result = decide(intent)

        assert result.decision is fixture.expected_decision, fixture.fixture_id
        assert result.reason_codes == fixture.expected_reason_codes, fixture.fixture_id
        assert (result.intent_id, result.intent_version) == (
            intent.intent_id,
            intent.version,
        )
        assert result.policy_version == "finance-v1"


def test_decisions_are_deterministic_and_have_expected_interactions() -> None:
    compiler = FixtureCompiler()

    for fixture in build_frozen_request_benchmark():
        intent = compiler.compile(fixture)
        first = decide(intent)
        second = decide(intent)

        assert first.model_dump_json() == second.model_dump_json()
        if first.decision is Decision.CLARIFY:
            assert first.questions
            assert first.required_approver is None
        elif first.decision is Decision.ESCALATE:
            assert first.questions == ()
            assert first.required_approver == "finance_manager"
        elif first.decision is Decision.REJECT:
            assert first.questions == ()
            assert first.required_approver is None


def test_precedence_repairs_preserve_frozen_fixture_outcomes() -> None:
    compiler = FixtureCompiler()
    fixtures = {
        fixture.fixture_id: fixture for fixture in build_frozen_request_benchmark()
    }

    low_value = decide(compiler.compile(fixtures["CG-APP-01"]))
    wildcard = decide(compiler.compile(fixtures["CG-REJ-08"]))
    no_tool_unbounded = decide(compiler.compile(fixtures["CG-CLR-10"]))
    contradictory = decide(compiler.compile(fixtures["CG-REJ-10"]))

    assert low_value.decision is Decision.APPROVE
    assert low_value.reason_codes == (ReasonCode.REQUEST_ADMISSIBLE.value,)
    assert wildcard.decision is Decision.REJECT
    assert wildcard.reason_codes == (ReasonCode.UNBOUNDED_PERMISSIONS.value,)
    assert no_tool_unbounded.decision is Decision.CLARIFY
    assert no_tool_unbounded.reason_codes == (ReasonCode.UNBOUNDED_PERMISSIONS.value,)
    assert contradictory.decision is Decision.REJECT
    assert contradictory.reason_codes == (ReasonCode.CONTRADICTORY_REQUIREMENTS.value,)


def test_high_value_payment_requires_finance_manager() -> None:
    fixture = next(
        item
        for item in build_frozen_request_benchmark()
        if item.fixture_id == "CG-ESC-01"
    )

    result = decide(FixtureCompiler().compile(fixture))

    assert result.decision is Decision.ESCALATE
    assert result.reason_codes == (
        ReasonCode.PAYMENT_ABOVE_AUTONOMOUS_LIMIT.value,
    )
    assert result.required_approver == "finance_manager"
