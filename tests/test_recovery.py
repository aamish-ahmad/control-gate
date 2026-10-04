"""C5 bounded recovery and same-episode memory acceptance tests."""

from datetime import datetime, timezone

import pytest

from control_gate import invoice_runtime as runtime
from control_gate.contracts import (
    Decision, EventType, ExecutionRun, HumanAction, HumanIntervention, RuntimeDecision,
    RunState,
)
from control_gate.human_control import intent_digest, scope
from control_gate.tool_environment import (
    FailureInjectingToolEnvironment, InjectedFailureMode, PurchaseOrderRecord,
    build_local_tool_environment,
)


def request(invoice="INV-1001", supplier="SUP-1001", po="PO-1001", amount="7500.00"):
    return (f"finance_agent process invoice {invoice} from supplier {supplier} under {po} "
            f"for USD {amount}; supplier exists, valid purchase order, not duplicate, "
            "and all validations pass.")


def injected(**failures):
    base = build_local_tool_environment()
    return base, FailureInjectingToolEnvironment(base, failures=failures)


def events(run, event_type, tool=None):
    return [event for event in run.events if event.event_type is event_type
            and (tool is None or event.tool == tool)]


def retry_boundary():
    _, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    completed = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    checks = events(completed, EventType.RUNTIME_POLICY_CHECK, "inspect_invoice")
    boundary = checks[1].sequence_number
    payload = completed.model_dump(mode="json")
    first_decision = next(event for event in payload["events"]
                          if event["event_type"] == "runtime_policy_check")
    payload.update(
        state="RUNNING", final_outcome=None,
        runtime_decision=first_decision["metadata"]["runtime_decision"],
        proposed_action=first_decision["metadata"]["proposal"],
        events=payload["events"][:boundary], evidence={},
        tool_history=payload["tool_history"][:1], observations=payload["observations"][:1],
        retry_state={"attempts": 1, "tool": "inspect_invoice",
            "last_error": "TOOL_TIMEOUT", "failed_action_id": payload["tool_history"][0],
            "max_retries": 2},
    )
    return ExecutionRun.model_validate(payload)


def test_explicit_timeout_retries_once_and_preserves_same_episode():
    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED
    assert len(base.staged_payments) == 1
    assert len(run.tool_history) == len(run.observations) == 7
    assert len(events(run, EventType.RUNTIME_POLICY_CHECK, "inspect_invoice")) == 2
    assert len(events(run, EventType.TOOL_CALL_STARTED, "inspect_invoice")) == 2
    assert [event.retry_count for event in events(run, EventType.RETRY_SCHEDULED)] == [1]
    assert run.retry_state == {"attempts": 0}
    assert all((event.run_id, event.intent_id, event.intent_version) ==
               (run.run_id, run.intent_id, run.intent_version) for event in run.events)


def test_plan_retries_only_idempotent_reads_with_finance_policy_cap():
    run = runtime.execute_invoice(runtime.DEMO_REQUEST)
    rules = {step.step_id: step.retry_rule for step in run.execution_plan.steps}
    assert all(rules[tool].max_retries == 2 for tool in runtime._TOOLS[:-1])
    assert all(rules[tool].retryable_conditions == (
        "TOOL_TIMEOUT", "MALFORMED_TOOL_RESPONSE") for tool in runtime._TOOLS[:-1])
    assert rules["stage_payment"].max_retries == 0
    assert rules["stage_payment"].retryable_conditions == ()


def test_malformed_responses_retry_to_cap_then_admit_only_typed_evidence():
    base, environment = injected(lookup_supplier=(
        InjectedFailureMode.MALFORMED_TOOL_RESPONSE,
        InjectedFailureMode.MALFORMED_TOOL_RESPONSE,
    ))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED and len(base.staged_payments) == 1
    assert [event.retry_count for event in events(
        run, EventType.RETRY_SCHEDULED, "lookup_supplier")] == [1, 2]
    assert sum(observation.get("error_type") == "_MalformedToolResponse"
               for observation in run.observations) == 2
    assert "malformed" not in run.evidence["lookup_supplier"]
    assert run.evidence["lookup_supplier"]["supplier_id"] == "SUP-1001"
    restored = ExecutionRun.model_validate_json(run.model_dump_json())
    assert restored == run


def test_every_read_can_recover_at_its_cap_without_replaying_completed_steps():
    modes = (InjectedFailureMode.TOOL_TIMEOUT, InjectedFailureMode.TOOL_TIMEOUT)
    base, environment = injected(**{tool: modes for tool in runtime._TOOLS[:-1]})
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED and len(base.staged_payments) == 1
    assert len(events(run, EventType.RETRY_SCHEDULED)) == 10
    assert len(run.tool_history) == len(run.observations) == 16
    assert [event.tool for event in events(run, EventType.TOOL_CALL_COMPLETED)] == list(
        runtime._TOOLS)


def test_repeated_transient_failure_stops_after_two_retries():
    base, environment = injected(retrieve_policy=(
        InjectedFailureMode.TOOL_TIMEOUT,
        InjectedFailureMode.TOOL_TIMEOUT,
        InjectedFailureMode.TOOL_TIMEOUT,
    ))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and "TOOL_TIMEOUT" in run.final_outcome.summary
    assert len(events(run, EventType.TOOL_CALL_STARTED, "retrieve_policy")) == 3
    assert [event.retry_count for event in events(
        run, EventType.RETRY_SCHEDULED, "retrieve_policy")] == [1, 2]
    assert run.retry_state["attempts"] == run.retry_state["max_retries"] == 2
    assert base.staged_payments == ()


def test_staging_is_never_automatically_retried():
    base, environment = injected(stage_payment=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and "TOOL_TIMEOUT" in run.final_outcome.summary
    assert len(events(run, EventType.TOOL_CALL_STARTED, "stage_payment")) == 1
    assert not events(run, EventType.RETRY_SCHEDULED, "stage_payment")
    assert base.staged_payments == ()


def test_permission_denial_is_terminal_and_never_bypassed():
    base, environment = injected(lookup_supplier=(InjectedFailureMode.PERMISSION_DENIED,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and "PERMISSION_DENIED" in run.final_outcome.summary
    assert len(events(run, EventType.TOOL_CALL_STARTED, "lookup_supplier")) == 1
    assert not events(run, EventType.RETRY_SCHEDULED)
    assert base.staged_payments == ()


@pytest.mark.parametrize("text,reason", [
    (request("INV-9999"), "RECORD_NOT_FOUND"),
    (request("INV-3001"), "DUPLICATE_INVOICE"),
])
def test_missing_record_and_duplicate_fail_safely_without_retry(text, reason):
    environment = build_local_tool_environment()
    run = runtime.execute_invoice(text, environment)
    assert reason in run.final_outcome.summary
    assert not events(run, EventType.RETRY_SCHEDULED)
    assert environment.staged_payments == ()


def test_po_invoice_contradiction_is_blocked_before_staging():
    class ContradictoryEnvironment:
        def __init__(self):
            self.base = build_local_tool_environment()

        def __getattr__(self, name):
            return getattr(self.base, name)

        def lookup_purchase_order(self, purchase_order_id):
            record = self.base.lookup_purchase_order(purchase_order_id)
            return PurchaseOrderRecord.model_validate({
                **record.model_dump(mode="json"), "supplier_id": "SUP-2001"})

    environment = ContradictoryEnvironment()
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.REJECTED
    assert run.runtime_decision.reason_codes == ("RUNTIME_EVIDENCE_CONTRADICTION",)
    assert not events(run, EventType.TOOL_CALL_STARTED, "stage_payment")
    assert environment.base.staged_payments == ()


def test_retry_reenters_gate_b_and_changed_resource_is_rejected(monkeypatch):
    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    original = runtime._propose

    def changed(run, tool):
        proposal = original(run, tool)
        if run.retry_state.get("attempts"):
            proposal["arguments"]["invoice_id"] = "INV-3001"
        return proposal

    monkeypatch.setattr(runtime, "_propose", changed)
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.REJECTED
    assert run.runtime_decision.reason_codes == ("RUNTIME_RESOURCE_UNAUTHORIZED",)
    assert len(events(run, EventType.RUNTIME_POLICY_CHECK, "inspect_invoice")) == 2
    assert len(events(run, EventType.TOOL_CALL_STARTED, "inspect_invoice")) == 1
    assert base.staged_payments == ()


def test_valid_episode_retry_boundary_is_gate_b_admissible():
    run = retry_boundary()
    proposal = runtime._propose(run, "inspect_invoice")
    decision = runtime.decide_runtime(run, proposal)
    assert decision.decision is Decision.APPROVE
    assert decision.reason_codes == ("RUNTIME_ACTION_ADMISSIBLE",)
    assert RuntimeDecision.model_validate(decision.model_dump()) == decision


@pytest.mark.parametrize("change", [
    {"attempts": 0},
    {"attempts": 3},
    {"tool": "stage_payment"},
    {"last_error": "PERMISSION_DENIED"},
    {"failed_action_id": "another-run:action:0"},
    {"max_retries": 99},
])
def test_forged_or_exhausted_retry_memory_cannot_dispatch(change):
    run = retry_boundary()
    state = run.model_dump(mode="json")["retry_state"]
    state.update(change)
    run.retry_state = state
    decision = runtime.decide_runtime(run, runtime._propose(run, "inspect_invoice"))
    assert decision.decision is Decision.REJECT
    assert decision.reason_codes[0] in {
        "RUNTIME_PRIOR_TOOL_FAILURE", "RUNTIME_RETRY_NOT_AUTHORIZED"}


@pytest.mark.parametrize("field,value", [
    ("retry_count", 2),
    ("tool", "lookup_supplier"),
    ("metadata.reason_codes", ["PERMISSION_DENIED"]),
    ("metadata.next_action_id", "wrong:action:1"),
])
def test_tampered_retry_event_cannot_dispatch(field, value):
    run = retry_boundary()
    event = run.events[-1]
    if field.startswith("metadata."):
        metadata = event.model_dump(mode="json")["metadata"]
        metadata[field.split(".", 1)[1]] = value
        event = event.model_copy(update={"metadata": metadata})
    else:
        event = event.model_copy(update={field: value})
    run.events = (*run.events[:-1], event)
    decision = runtime.decide_runtime(run, runtime._propose(run, "inspect_invoice"))
    assert decision.decision is Decision.REJECT
    assert decision.reason_codes[0] in {
        "RUNTIME_PRIOR_TOOL_FAILURE", "RUNTIME_RETRY_NOT_AUTHORIZED"}


def test_human_stop_is_not_a_retry_source():
    high = runtime.DEMO_REQUEST.replace("1001", "2001").replace("7500.00", "18400.00")
    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(high, environment)
    assert run.state is RunState.ESCALATION_REQUIRED and run.tool_history == ()
    intervention = HumanIntervention(
        intervention_id="H-C5-DENY", run_id=run.run_id, intent_id=run.intent_id,
        intent_version=run.intent_version, timestamp=datetime.now(timezone.utc),
        actor_id="human-manager", actor_role="finance_manager", action=HumanAction.DENY,
        reason="Do not execute", constraint_changes={"intent_digest": intent_digest(run.intent_spec)},
    )
    assert runtime.resume_invoice(run, intervention).state is RunState.REJECTED
    assert not events(run, EventType.RETRY_SCHEDULED)
    assert base.staged_payments == ()


def test_human_approved_child_recovery_keeps_exact_approval_scope():
    high = runtime.DEMO_REQUEST.replace("1001", "2001").replace("7500.00", "18400.00")
    base, environment = injected(lookup_supplier=(InjectedFailureMode.TOOL_TIMEOUT,))
    parent = runtime.execute_invoice(high, environment)
    intervention = HumanIntervention(
        intervention_id="H-C5-APPROVE", run_id=parent.run_id, intent_id=parent.intent_id,
        intent_version=parent.intent_version, timestamp=datetime.now(timezone.utc),
        actor_id="human-manager", actor_role="finance_manager", action=HumanAction.APPROVE,
        reason="Approve exact reviewed invoice", constraint_changes={
            "intent_digest": intent_digest(parent.intent_spec),
            "approved_action": scope(parent.intent_spec),
        },
    )
    child = runtime.resume_invoice(parent, intervention)
    assert child.state is RunState.COMPLETED and child.parent_run_id == parent.run_id
    assert child.human_approval == intervention and len(base.staged_payments) == 1
    assert [event.retry_count for event in events(child, EventType.RETRY_SCHEDULED)] == [1]
    assert all(event.decision == Decision.APPROVE.value for event in events(
        child, EventType.RUNTIME_POLICY_CHECK))
