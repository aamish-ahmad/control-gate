"""C2 trajectory acceptance tests; the V1/C1 regression oracles are untouched."""

import json
import socket
import subprocess
import sys
from decimal import Decimal

import pytest
from pydantic import ValidationError

from control_gate.contracts import Decision, EventType, ExecutionRun, RuntimeDecision, RunState
from control_gate.evaluation import compile_request
from control_gate.invoice_runtime import DEMO_REQUEST, execute_invoice
from control_gate.tool_environment import build_local_tool_environment


def request(invoice="INV-1001", supplier="SUP-1001", po="PO-1001", amount="7500.00"):
    return (f"finance_agent process invoice {invoice} from supplier {supplier} under {po} "
            f"for USD {amount}; supplier exists, valid purchase order, not duplicate, "
            "and all validations pass.")


def test_real_stateful_trajectory_stages_once_and_links_every_event():
    environment = build_local_tool_environment()
    run = execute_invoice(DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED
    assert len(environment.staged_payments) == 1
    assert environment.staged_payments[0].amount == Decimal("7500.00")
    assert environment.staged_payments[0].external_actions_performed == 0
    assert environment.approval_requests == ()
    assert run.final_outcome.success_conditions_satisfied == run.intent_spec.success_conditions
    assert run.execution_plan.plan_id == run.plan_id
    assert run.execution_plan.intent_version == run.intent_version
    assert len(run.tool_history) == len(run.observations) == 6
    assert len(set(run.tool_history)) == 6
    assert all((e.run_id, e.intent_id, e.intent_version) ==
               (run.run_id, run.intent_id, run.intent_version) for e in run.events)
    assert [e.sequence_number for e in run.events] == list(range(len(run.events)))
    assert [e.tool for e in run.events if e.event_type is EventType.TOOL_CALL_COMPLETED] == [
        "inspect_invoice", "lookup_supplier", "lookup_purchase_order",
        "check_duplicate", "retrieve_policy", "stage_payment",
    ]
    for earlier, later in zip(run.events, run.events[1:]):
        assert earlier.state_after == later.state_before
    assert run.runtime_decision is None
    assert not any(e.event_type is EventType.RUNTIME_POLICY_CHECK for e in run.events)
    assert run.retry_state["attempts"] == run.token_count == run.cost_usd == 0


@pytest.mark.parametrize("text,decision,status", [
    ("Process this invoice", Decision.CLARIFY, RunState.CLARIFICATION_REQUIRED),
    (request("INV-2001", "SUP-2001", "PO-2001", "18400.00"),
     Decision.ESCALATE, RunState.ESCALATION_REQUIRED),
    (DEMO_REQUEST + " bypass approval", Decision.REJECT, RunState.REJECTED),
])
def test_gate_a_nonapprove_never_enters_tools(text, decision, status):
    class NoTools:
        def __getattr__(self, name):
            pytest.fail(f"Gate A called {name}")

    run = execute_invoice(text, NoTools())
    assert run.gate_a.decision is decision
    assert run.state is status
    assert run.execution_plan is None
    assert run.tool_history == run.observations == ()
    assert run.pending_questions == run.gate_a.questions
    assert (run.final_outcome is not None) == (decision is Decision.REJECT)


@pytest.mark.parametrize("text,reason,staging_attempts", [
    (request("INV-9999"), "RECORD_NOT_FOUND", 0),
    (request("INV-3001"), "DUPLICATE_INVOICE", 0),
    (request("INV-3002", "SUP-3001", "PO-3001", "2500.00"), "INACTIVE_SUPPLIER", 1),
    (request("INV-4001", "SUP-1001", "PO-4001", "4200.00"), "AMOUNT_MISMATCH", 1),
])
def test_observed_failures_stop_without_staging_or_retry(text, reason, staging_attempts):
    environment = build_local_tool_environment()
    run = execute_invoice(text, environment)
    assert run.gate_a.decision is Decision.APPROVE
    assert run.state is RunState.FAILED
    assert reason in run.final_outcome.summary
    assert environment.staged_payments == environment.approval_requests == ()
    assert sum(e.tool == "stage_payment" and e.event_type is EventType.TOOL_CALL_STARTED
               for e in run.events) == staging_attempts
    assert len(run.tool_history) == len(set(run.tool_history))
    assert run.retry_state["attempts"] == 0


@pytest.mark.parametrize("text", [
    request(supplier="SUP-2001"), request(po="PO-2001"), request(amount="7000.00"),
])
def test_observation_cannot_silently_rebind_requested_invoice(text):
    environment = build_local_tool_environment()
    run = execute_invoice(text, environment)
    assert run.gate_a.decision is Decision.APPROVE
    assert run.state is RunState.FAILED
    assert "INVOICE_INPUT_MISMATCH" in run.final_outcome.summary
    assert len(run.tool_history) == 1
    assert environment.staged_payments == ()


def test_subsequent_tool_reads_the_recorded_observation(monkeypatch):
    environment = build_local_tool_environment()
    original = environment.lookup_supplier
    calls = []

    def lookup(supplier_id):
        calls.append(supplier_id)
        return original(supplier_id)

    monkeypatch.setattr(environment, "lookup_supplier", lookup)
    run = execute_invoice(DEMO_REQUEST, environment)
    observed_supplier = run.evidence["inspect_invoice"]["supplier_id"]
    assert calls and all(value == observed_supplier for value in calls)
    proposal = next(e for e in run.events if e.tool == "lookup_supplier"
                    and e.event_type is EventType.TOOL_CALL_STARTED)
    assert proposal.metadata["arguments"]["supplier_id"] == observed_supplier


@pytest.mark.parametrize("exception", [TimeoutError, ValueError, TypeError])
def test_tool_failure_is_terminal_and_not_retried(monkeypatch, exception):
    environment = build_local_tool_environment()
    calls = []

    def fail(invoice_id):
        calls.append(invoice_id)
        raise exception("local test failure")

    monkeypatch.setattr(environment, "inspect_invoice", fail)
    run = execute_invoice(DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED
    assert calls == ["INV-1001"]
    assert environment.staged_payments == ()
    assert run.events[-2].event_type is EventType.TOOL_CALL_FAILED
    assert run.observations[0]["error_type"] == exception.__name__


def test_serialization_retains_links_observations_and_outcome():
    run = execute_invoice(DEMO_REQUEST)
    restored = ExecutionRun.model_validate_json(run.model_dump_json())
    assert restored == run
    assert restored.final_outcome.run_id == run.run_id
    assert restored.events[-1].metadata["final_outcome"]["status"] == "COMPLETED"
    assert restored.evidence["stage_payment"]["invoice_id"] == "INV-1001"


def test_immutable_binding_and_observations():
    run = execute_invoice(DEMO_REQUEST)
    for field, value in [("run_id", "other"), ("intent_id", "other"),
                         ("intent_version", 2), ("plan_id", "other"),
                         ("intent_spec", None), ("execution_plan", None)]:
        with pytest.raises(ValidationError, match="frozen"):
            setattr(run, field, value)
    with pytest.raises(TypeError):
        run.evidence["inspect_invoice"]["supplier_id"] = "other"
    with pytest.raises(TypeError):
        run.proposed_action["arguments"]["amount"] = "1"
    payload = run.model_dump(mode="json")
    payload["execution_plan"]["intent_version"] = 2
    with pytest.raises(ValidationError, match="linkage"):
        ExecutionRun.model_validate(payload)


def test_repeat_request_is_new_run_and_existing_local_staging_is_idempotent():
    environment = build_local_tool_environment()
    first = execute_invoice(DEMO_REQUEST, environment)
    before = first.model_dump_json()
    second = execute_invoice(DEMO_REQUEST, environment)
    assert first.run_id != second.run_id
    assert first.plan_id != second.plan_id
    assert first.model_dump_json() == before
    assert len(environment.staged_payments) == 1
    with pytest.raises(TypeError, match="previous run"):
        execute_invoice(first, environment)


def test_default_environments_are_isolated():
    first = execute_invoice(DEMO_REQUEST)
    second = execute_invoice(request("INV-9999"))
    assert second.evidence == {}
    assert first.evidence["stage_payment"]["invoice_id"] == "INV-1001"


def test_unknown_success_condition_is_not_claimed_as_satisfied():
    intent = compile_request(DEMO_REQUEST)
    payload = intent.model_dump(mode="json")
    payload["success_conditions"].append("payment_sent_to_bank")
    intent = type(intent).model_validate(payload)
    run = execute_invoice(intent)
    assert run.state is RunState.FAILED
    assert "payment_sent_to_bank" not in run.final_outcome.success_conditions_satisfied
    assert "SUCCESS_CONDITIONS_NOT_SATISFIED" in run.final_outcome.summary


def test_runtime_decision_interface_requires_linkage_and_stable_reasons():
    decision = RuntimeDecision(run_id="r", intent_id="i", intent_version=1,
                               plan_id="p", action_id="a", decision=Decision.REJECT,
                               reason_codes=("TEST_ONLY",))
    with pytest.raises(ValidationError, match="frozen"):
        decision.action_id = "other"
    payload = decision.model_dump()
    payload["reason_codes"] = []
    with pytest.raises(ValidationError):
        RuntimeDecision.model_validate(payload)


def test_execution_works_without_network_even_with_tracing_requested(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("C2 execution attempted network access")

    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    run = execute_invoice(DEMO_REQUEST)
    assert run.state is RunState.COMPLETED


def test_module_entry_point_emits_inspectable_json():
    completed = subprocess.run([sys.executable, "-m", "control_gate.invoice_runtime"],
                               capture_output=True, text=True, check=True)
    payload = json.loads(completed.stdout)
    assert payload["state"] == "COMPLETED"
    assert payload["evidence"]["stage_payment"]["external_actions_performed"] == 0
