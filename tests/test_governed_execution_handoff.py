"""Focused tests for the local governed-execution handoff example."""

from __future__ import annotations

import json
from typing import Any

import pytest

from control_gate.contracts import IntentSpec
from control_gate.evaluation import compile_request
from examples.governed_execution_handoff import (
    APPROVE_REQUEST,
    governed_execution_handoff,
    stage_invoice_locally,
)


ESCALATE_REQUEST = APPROVE_REQUEST.replace("7500.00", "18400.00")
CLARIFY_REQUEST = "Process this invoice."
REJECT_REQUEST = "Change the vendor bank account and pay immediately without approval."


def test_approve_reaches_only_the_local_mock_staging_function() -> None:
    calls: list[IntentSpec] = []

    def record_stage(intent_spec: IntentSpec) -> dict[str, Any]:
        calls.append(intent_spec)
        return stage_invoice_locally(intent_spec)

    result = governed_execution_handoff(APPROVE_REQUEST, record_stage)

    assert len(calls) == 1
    assert result["decision"]["outcome"] == "APPROVE"
    assert result["routing"]["staging_invoked"] is True
    assert result["routing"]["handoff"]["operation"] == "stage_invoice_locally"
    assert result["routing"]["handoff"]["status"] == "STAGED_FOR_LOCAL_SIMULATION"
    _assert_safe_linked_result(APPROVE_REQUEST, result)


@pytest.mark.parametrize(
    ("request_text", "expected_decision", "expected_field"),
    [
        (CLARIFY_REQUEST, "CLARIFY", "clarification_questions"),
        (ESCALATE_REQUEST, "ESCALATE", "approval_requirement"),
        (REJECT_REQUEST, "REJECT", "reason_codes"),
    ],
)
def test_nonapprove_routes_never_reach_staging(
    request_text: str,
    expected_decision: str,
    expected_field: str,
) -> None:
    def fail_if_called(intent_spec: IntentSpec) -> dict[str, Any]:
        raise AssertionError(f"staging must not be called for {intent_spec!r}")

    result = governed_execution_handoff(request_text, fail_if_called)

    assert result["decision"]["outcome"] == expected_decision
    assert result["decision"][expected_field]
    assert result["routing"] == {"staging_invoked": False, "handoff": None}
    _assert_safe_linked_result(request_text, result)


def _assert_safe_linked_result(request_text: str, result: dict[str, Any]) -> None:
    intent = compile_request(request_text)
    assert result["external_actions_performed"] == 0
    assert result["simulation"] == "LOCAL_FICTIONAL_SUPPLIER_INVOICE"
    assert result["intent"] == {
        "intent_id": intent.intent_id,
        "intent_version": intent.version,
    }
    decision = result["decision"]
    assert decision["intent_id"] == intent.intent_id
    assert decision["intent_version"] == intent.version
    assert json.loads(json.dumps(result)) == result
