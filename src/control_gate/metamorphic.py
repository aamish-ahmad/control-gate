"""Metamorphic testing generators for Control Gate."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from control_gate.compiler import RequestFixture
from control_gate.contracts import Decision


@dataclass
class MetamorphicCase:
    original_fixture_id: str
    mutation_type: str
    mutated_fixture: RequestFixture
    expected_decision: Decision
    expected_reason_codes: tuple[str, ...]
    is_invariant: bool
    proves: str


def _update_fixture(fixture: RequestFixture, request: str | None = None, context_updates: dict | None = None) -> RequestFixture:
    payload = fixture.model_dump(mode="python")
    if request is not None:
        payload["request"] = request
    if context_updates is not None:
        payload["context"].update(context_updates)
    return RequestFixture.model_validate(payload)


def generate_metamorphic_cases(fixture: RequestFixture) -> Iterator[MetamorphicCase]:
    """Generate metamorphic cases for a given fixture."""

    # 1. Non-semantic text mutation (Proves: Compiler decisions are strictly driven by structured context, not NL wording)
    yield MetamorphicCase(
        original_fixture_id=fixture.fixture_id,
        mutation_type="non_semantic_request_formatting",
        mutated_fixture=_update_fixture(fixture, request=fixture.request.lower() + " [modified]"),
        expected_decision=fixture.expected_decision,
        expected_reason_codes=fixture.expected_reason_codes,
        is_invariant=True,
        proves="Request string mutations do not alter intent or policy evaluation, which relies strictly on context.",
    )

    # 2. Context Invariant: Safe assumptions (Proves: Adding benign assumptions does not trigger UNSAFE_ASSUMPTION rejection)
    if fixture.expected_decision == Decision.APPROVE:
        yield MetamorphicCase(
            original_fixture_id=fixture.fixture_id,
            mutation_type="add_safe_assumption",
            mutated_fixture=_update_fixture(
                fixture,
                context_updates={"assumptions": fixture.context.assumptions + ("assume_invoice_date_is_today",)}
            ),
            expected_decision=Decision.APPROVE,
            expected_reason_codes=("REQUEST_ADMISSIBLE",),
            is_invariant=True,
            proves="Adding non-prohibited assumptions preserves admissible status without triggering validation errors.",
        )

        # 3. Boundary Mutation: Amount limits (Proves: The threshold correctly escalates payments strictly above $10,000)
        yield MetamorphicCase(
            original_fixture_id=fixture.fixture_id,
            mutation_type="boundary_amount_below",
            mutated_fixture=_update_fixture(fixture, context_updates={"amount": "9999.99"}),
            expected_decision=Decision.APPROVE,
            expected_reason_codes=("REQUEST_ADMISSIBLE",),
            is_invariant=False,
            proves="Amounts strictly below the limit remain autonomously admissible.",
        )

        yield MetamorphicCase(
            original_fixture_id=fixture.fixture_id,
            mutation_type="boundary_amount_exact",
            mutated_fixture=_update_fixture(fixture, context_updates={"amount": "10000.00"}),
            expected_decision=Decision.APPROVE,
            expected_reason_codes=("REQUEST_ADMISSIBLE",),
            is_invariant=False,
            proves="Amounts exactly at the limit remain autonomously admissible.",
        )

        yield MetamorphicCase(
            original_fixture_id=fixture.fixture_id,
            mutation_type="boundary_amount_above",
            mutated_fixture=_update_fixture(fixture, context_updates={"amount": "10000.01"}),
            expected_decision=Decision.ESCALATE,
            expected_reason_codes=("PAYMENT_ABOVE_AUTONOMOUS_LIMIT",),
            is_invariant=False,
            proves="Amounts strictly above the limit correctly trigger escalation.",
        )
