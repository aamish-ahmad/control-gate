"""Phase 1 acceptance tests for the frozen V1 contracts."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from control_gate.contracts import (
    FINANCE_V1_POLICY,
    REQUEST_ADMISSIBILITY_LABELS,
    RUNTIME_BENCHMARK_BUCKETS,
    ApprovalRule,
    ControlDecision,
    Decision,
    EventType,
    ExecutionPlan,
    ExecutionRun,
    Goal,
    HumanAction,
    HumanIntervention,
    IntentActor,
    IntentSpec,
    Permissions,
    PlanStep,
    RetryRule,
    RunOutcome,
    RunState,
    TrajectoryEvent,
)


def invoice_intent() -> IntentSpec:
    return IntentSpec(
        intent_id="INT-2049",
        version=1,
        source_request="Process this supplier invoice and pay it if everything looks correct.",
        goal=Goal(type="process_supplier_invoice"),
        actor=IntentActor(id="finance_agent", role="automated_finance_operator"),
        inputs={
            "invoice_id": "INV-1442",
            "vendor_id": "VENDOR-18",
            "purchase_order_id": "PO-882",
        },
        assumptions=("vendor_record_is_authoritative", "invoice_currency_is_usd"),
        requirements=(
            "verify_vendor",
            "validate_purchase_order",
            "detect_duplicate_invoice",
            "verify_amount",
        ),
        constraints={"max_autonomous_payment": 10000, "currency": "USD"},
        permissions=Permissions(
            allowed_tools=(
                "invoice.parse",
                "vendor.lookup",
                "po.lookup",
                "payment.submit",
            )
        ),
        prohibited_actions=(
            "vendor.modify_bank_details",
            "payment.bypass_approval",
        ),
        approval_rules=(ApprovalRule(when="amount > 10000", require="finance_manager"),),
        risk_level="medium",
        success_conditions=(
            "invoice_validated",
            "payment_authorized",
            "audit_event_written",
        ),
        failure_conditions=(
            "vendor_missing",
            "duplicate_invoice",
            "purchase_order_mismatch",
            "approval_denied",
        ),
        rollback_strategy=("cancel_unsubmitted_payment",),
    )


def test_intent_spec_matches_frozen_v1_schema_and_is_immutable() -> None:
    intent = invoice_intent()

    assert set(intent.model_dump()) == {
        "intent_id",
        "version",
        "source_request",
        "goal",
        "actor",
        "inputs",
        "assumptions",
        "requirements",
        "constraints",
        "permissions",
        "prohibited_actions",
        "approval_rules",
        "risk_level",
        "success_conditions",
        "failure_conditions",
        "rollback_strategy",
    }
    with pytest.raises(ValidationError, match="frozen"):
        intent.version = 2


def test_contracts_reject_unfrozen_fields() -> None:
    payload = invoice_intent().model_dump()
    payload["unresolved_fields"] = ["amount"]

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        IntentSpec.model_validate(payload)


def test_control_decision_is_structured_and_intent_linked() -> None:
    decision = ControlDecision(
        decision=Decision.ESCALATE,
        reason_codes=("PAYMENT_ABOVE_AUTONOMOUS_LIMIT",),
        blocking_fields=(),
        questions=(),
        required_approver="finance_manager",
        policy_version="finance-v1",
        intent_id="INT-2049",
        intent_version=1,
    )

    assert decision.decision is Decision.ESCALATE
    assert (decision.intent_id, decision.intent_version) == ("INT-2049", 1)


def test_plan_and_run_preserve_the_authorizing_intent_version() -> None:
    plan = ExecutionPlan(
        plan_id="PLAN-2049",
        intent_id="INT-2049",
        intent_version=1,
        steps=(
            PlanStep(
                step_id="lookup_vendor",
                tool_requirements=("vendor.lookup",),
                policy_checkpoints=("P1",),
                retry_rule=RetryRule(
                    max_retries=2,
                    retryable_conditions=("transient_timeout",),
                ),
            ),
            PlanStep(
                step_id="submit_payment",
                dependencies=("lookup_vendor",),
                tool_requirements=("payment.submit",),
                policy_checkpoints=("P8", "P10"),
                approval_checkpoints=("P6",),
                retry_rule=RetryRule(max_retries=0),
            ),
        ),
        terminal_success_state=RunState.COMPLETED,
        terminal_failure_states=(
            RunState.REJECTED,
            RunState.FAILED,
            RunState.CANCELLED,
        ),
    )
    run = ExecutionRun(
        run_id="RUN-2049",
        intent_id=plan.intent_id,
        intent_version=plan.intent_version,
        plan_id=plan.plan_id,
        state=RunState.CREATED,
    )

    run.state = RunState.COMPILING
    assert run.state is RunState.COMPILING
    with pytest.raises(ValidationError, match="frozen"):
        run.intent_version = 2


def test_trajectory_and_human_intervention_are_intent_linked() -> None:
    timestamp = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
    event = TrajectoryEvent(
        event_id="EVT-1",
        run_id="RUN-2049",
        intent_id="INT-2049",
        intent_version=1,
        timestamp=timestamp,
        sequence_number=1,
        step_id="request_approval",
        actor="finance_agent",
        event_type=EventType.HUMAN_APPROVAL_REQUESTED,
        state_before=RunState.RUNNING.value,
        state_after=RunState.WAITING_FOR_HUMAN.value,
        policy_checks=("P6",),
        decision=Decision.ESCALATE.value,
        status="completed",
    )
    intervention = HumanIntervention(
        intervention_id="HITL-1",
        run_id=event.run_id,
        intent_id=event.intent_id,
        intent_version=event.intent_version,
        timestamp=timestamp,
        actor_id="FIN-MGR-7",
        actor_role="finance_manager",
        action=HumanAction.APPROVE,
        reason="Invoice and purchase order verified.",
    )

    assert event.intent_version == intervention.intent_version == 1
    assert intervention.action is HumanAction.APPROVE


def test_run_outcome_must_use_a_terminal_state() -> None:
    payload = {
        "outcome_id": "OUT-1",
        "run_id": "RUN-2049",
        "intent_id": "INT-2049",
        "intent_version": 1,
        "status": RunState.RUNNING,
        "success_conditions_satisfied": (),
        "failure_conditions_triggered": (),
        "completed_at": datetime(2026, 7, 31, 12, 1, tzinfo=timezone.utc),
        "summary": "Run has not reached a terminal state.",
    }

    with pytest.raises(ValidationError, match="status must be terminal"):
        RunOutcome(**payload)

    payload["status"] = RunState.COMPLETED
    outcome = RunOutcome(**payload)
    assert outcome.status is RunState.COMPLETED


def test_finance_v1_policy_encodes_all_ten_frozen_rules() -> None:
    assert FINANCE_V1_POLICY.rule_ids == tuple(f"P{index}" for index in range(1, 11))
    assert FINANCE_V1_POLICY.vendor_must_exist is True
    assert FINANCE_V1_POLICY.agent_may_modify_vendor_bank_details is False
    assert FINANCE_V1_POLICY.valid_purchase_order_required is True
    assert FINANCE_V1_POLICY.duplicate_invoice_decision is Decision.REJECT
    assert FINANCE_V1_POLICY.max_autonomous_payment_usd == Decimal("10000")
    assert FINANCE_V1_POLICY.required_approver_above_limit == "finance_manager"
    assert FINANCE_V1_POLICY.bypass_approval_decision is Decision.REJECT
    assert FINANCE_V1_POLICY.payment_requires_all_validations is True
    assert FINANCE_V1_POLICY.transient_read_max_retries == 2
    assert FINANCE_V1_POLICY.uncertain_payment_auto_retry is False


def test_frozen_benchmark_labels_and_counts_are_representable() -> None:
    assert REQUEST_ADMISSIBILITY_LABELS == tuple(Decision)
    assert len(REQUEST_ADMISSIBILITY_LABELS) * 12 == 48
    assert RUNTIME_BENCHMARK_BUCKETS == (
        "allowed",
        "require escalation",
        "prohibited",
        "retry/fail-safe",
    )
    assert len(RUNTIME_BENCHMARK_BUCKETS) * 4 == 16
