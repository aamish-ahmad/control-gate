"""C3 adversarial proof at the actual dispatch boundary, with observed call spies."""

from copy import deepcopy

import pytest

from control_gate import invoice_runtime as runtime
from control_gate.contracts import Decision, EventType, ExecutionRun, IntentSpec, RunState
from control_gate.evaluation import compile_request
from control_gate.runtime_admissibility import INVOICE_TOOLS, decide_runtime
from control_gate.tool_environment import build_local_tool_environment


class ToolSpy:
    def __init__(self):
        self.calls = []
        self.environment = build_local_tool_environment()

    def __getattr__(self, tool):
        def invoke(**arguments):
            self.calls.append((tool, arguments))
            return getattr(self.environment, tool)(**arguments)
        return invoke


@pytest.fixture(scope="module")
def approved_trace():
    run = runtime.execute_invoice(runtime.DEMO_REQUEST)
    assert run.state is RunState.COMPLETED
    return run.model_dump(mode="json")


def before_tool(trace, tool="stage_payment"):
    """Use an actual completed trace's prefix; no public resume API is introduced."""
    payload = deepcopy(trace)
    index = INVOICE_TOOLS.index(tool)
    boundary = next(e["sequence_number"] for e in payload["events"]
                    if e["event_type"] == "runtime_policy_check" and e["tool"] == tool)
    payload.update(state="RUNNING", final_outcome=None, runtime_decision=None,
                   proposed_action=None, events=payload["events"][:boundary],
                   evidence={k: v for k, v in payload["evidence"].items()
                             if k in INVOICE_TOOLS[:index]},
                   tool_history=payload["tool_history"][:index],
                   observations=payload["observations"][:index])
    return ExecutionRun.model_validate(payload)


def assert_blocked(run, proposal, code, decision=Decision.REJECT):
    spy = ToolSpy()
    previous = len(run.events)
    expected = decide_runtime(run, proposal)
    assert expected == decide_runtime(run, proposal)
    assert expected.decision is decision
    assert expected.reason_codes == (code,)
    runtime._dispatch(run, spy, proposal)
    assert spy.calls == []
    assert spy.environment.staged_payments == ()
    assert not any(e.event_type is EventType.TOOL_CALL_STARTED for e in run.events[previous:])
    assert run.runtime_decision == expected
    event = run.events[previous]
    assert event.event_type is EventType.RUNTIME_POLICY_CHECK
    assert event.metadata["runtime_decision"]["action_id"] == expected.action_id
    assert ExecutionRun.model_validate_json(run.model_dump_json()) == run


@pytest.mark.parametrize("field,value,code", [
    ("tool", "wire.transfer", "RUNTIME_TOOL_PROHIBITED"),
    ("tool", "vendor.modify_bank_details", "RUNTIME_TOOL_PROHIBITED"),
    ("tool", "request_human_approval", "RUNTIME_TOOL_PROHIBITED"),
    ("goal", "delete_invoice_history", "RUNTIME_SCOPE_VIOLATION"),
    ("actor_id", "another_actor", "RUNTIME_ACTOR_UNAUTHORIZED"),
    ("actor_role", "external_contractor", "RUNTIME_ACTOR_UNAUTHORIZED"),
    ("assumptions", ["assume_po_valid_without_lookup"], "RUNTIME_UNSAFE_ASSUMPTION"),
    ("run_id", "another_run", "RUNTIME_LINKAGE_MISMATCH"),
    ("intent_id", "another_intent", "RUNTIME_LINKAGE_MISMATCH"),
    ("intent_version", 2, "RUNTIME_LINKAGE_MISMATCH"),
    ("plan_id", "another_plan", "RUNTIME_LINKAGE_MISMATCH"),
    ("action_id", "reused_action", "RUNTIME_LINKAGE_MISMATCH"),
])
def test_unauthorized_proposal_never_reaches_tool(approved_trace, field, value, code):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    proposal[field] = value
    assert_blocked(run, proposal, code)


@pytest.mark.parametrize("field,value,code", [
    ("invoice_id", "INV-3001", "RUNTIME_RESOURCE_UNAUTHORIZED"),
    ("purchase_order_id", "PO-2001", "RUNTIME_RESOURCE_UNAUTHORIZED"),
    ("currency", "EUR", "RUNTIME_RESOURCE_UNAUTHORIZED"),
    ("amount", "7500.01", "RUNTIME_AMOUNT_OUTSIDE_CONTRACT"),
    ("amount", "7000", "RUNTIME_AMOUNT_OUTSIDE_CONTRACT"),
    ("amount", "10000.01", "RUNTIME_AMOUNT_OUTSIDE_CONTRACT"),
    ("amount", "NaN", "RUNTIME_AMOUNT_INVALID"),
    ("amount", "Infinity", "RUNTIME_AMOUNT_INVALID"),
    ("amount", "0", "RUNTIME_AMOUNT_INVALID"),
    ("amount", True, "RUNTIME_AMOUNT_INVALID"),
    ("bypass_approval", True, "RUNTIME_ARGUMENTS_INVALID"),
])
def test_unauthorized_arguments_never_reach_tool(approved_trace, field, value, code):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    proposal["arguments"][field] = value
    assert_blocked(run, proposal, code)


@pytest.mark.parametrize("tool,key,value", [
    ("inspect_invoice", "invoice_id", "INV-3001"),
    ("lookup_supplier", "supplier_id", "SUP-2001"),
    ("lookup_purchase_order", "purchase_order_id", "PO-2001"),
    ("check_duplicate", "invoice_id", "INV-3001"),
    ("retrieve_policy", "policy_version", "permissive-policy"),
])
def test_every_read_is_guarded_too(approved_trace, tool, key, value):
    run = before_tool(approved_trace, tool)
    proposal = runtime._propose(run, tool)
    proposal["arguments"][key] = value
    assert_blocked(run, proposal, "RUNTIME_RESOURCE_UNAUTHORIZED")


@pytest.mark.parametrize("field", INVOICE_TOOLS[:-1])
def test_missing_evidence_clarifies_without_staging(approved_trace, field):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    evidence = run.model_dump(mode="json")["evidence"]
    del evidence[field]
    run.evidence = evidence
    assert_blocked(run, proposal, "RUNTIME_EVIDENCE_MISSING", Decision.CLARIFY)
    assert run.state is RunState.CLARIFICATION_REQUIRED
    assert run.pending_questions and run.final_outcome is None


def test_tampered_observation_is_not_authoritative(approved_trace):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    evidence = run.model_dump(mode="json")["evidence"]
    evidence["lookup_purchase_order"]["remaining_amount"] = "99999"
    run.evidence = evidence
    assert_blocked(run, proposal, "RUNTIME_EVIDENCE_INVALID")


@pytest.mark.parametrize("event_type,decision,code", [
    (EventType.RUNTIME_POLICY_CHECK, "REJECT", "RUNTIME_PRIOR_CONTROL_STOP"),
    (EventType.RUNTIME_POLICY_CHECK, "CLARIFY", "RUNTIME_PRIOR_CONTROL_STOP"),
    (EventType.RUNTIME_POLICY_CHECK, "ESCALATE", "RUNTIME_PRIOR_CONTROL_STOP"),
    (EventType.TOOL_CALL_FAILED, None, "RUNTIME_PRIOR_TOOL_FAILURE"),
])
def test_new_action_id_cannot_bypass_prior_stop(approved_trace, event_type, decision, code):
    run = before_tool(approved_trace)
    event = run.events[-1].model_copy(update={"event_type": event_type, "decision": decision})
    run.events += (event, event)
    assert_blocked(run, runtime._propose(run, "stage_payment"), code)


def test_retry_state_cannot_grant_authority(approved_trace):
    run = before_tool(approved_trace)
    run.retry_state = {"attempts": 1}
    assert_blocked(run, runtime._propose(run, "stage_payment"), "RUNTIME_RETRY_NOT_AUTHORIZED")


@pytest.mark.parametrize("state", ["REQUIRED", "DENIED", "CANCELLED", "APPROVED", "MODIFIED"])
def test_human_state_cannot_silently_grant_new_authority(approved_trace, state):
    run = before_tool(approved_trace)
    run.approval_state = state
    assert_blocked(run, runtime._propose(run, "stage_payment"),
                   "RUNTIME_HUMAN_AUTHORITY_REQUIRED", Decision.ESCALATE)
    assert run.state is RunState.ESCALATION_REQUIRED
    assert run.final_outcome is None


def test_human_override_event_requires_stop_even_if_approval_flag_was_cleared(approved_trace):
    run = before_tool(approved_trace)
    run.events += (run.events[-1].model_copy(update={"event_type": EventType.HUMAN_INTERVENTION}),)
    assert_blocked(run, runtime._propose(run, "stage_payment"),
                   "RUNTIME_HUMAN_AUTHORITY_REQUIRED", Decision.ESCALATE)


@pytest.mark.parametrize("change,expected", [
    ({"permissions": {"allowed_tools": ["invoice.parse", "vendor.lookup", "po.lookup"]}},
     "RUNTIME_TOOL_UNAUTHORIZED"),
    ({"permissions": {"allowed_tools": []}}, "RUNTIME_TOOL_UNAUTHORIZED"),
    ({"prohibited_actions": ["stage_payment"]}, "RUNTIME_TOOL_PROHIBITED"),
    ({"prohibited_actions": ["payment.submit"]}, "RUNTIME_TOOL_PROHIBITED"),
    ({"prohibited_actions": ["submit_payment"]}, "RUNTIME_TOOL_PROHIBITED"),
    ({"requirements": ["do_not_submit_payment"]}, "RUNTIME_TOOL_PROHIBITED"),
])
def test_gate_a_approval_does_not_bypass_runtime_permissions(change, expected):
    payload = compile_request(runtime.DEMO_REQUEST).model_dump(mode="json")
    payload.update(change)
    spy = ToolSpy()
    run = runtime.execute_invoice(IntentSpec.model_validate(payload), spy)
    assert run.gate_a.decision is Decision.APPROVE
    assert run.runtime_decision.reason_codes == (expected,)
    assert run.state is RunState.REJECTED
    assert not any(tool == "stage_payment" for tool, _ in spy.calls)
    if not payload["permissions"]["allowed_tools"]:
        assert spy.calls == []


def test_intent_cap_is_enforced_even_when_gate_a_approves():
    payload = compile_request(runtime.DEMO_REQUEST).model_dump(mode="json")
    payload["constraints"]["max_autonomous_payment_usd"] = "5000"
    spy = ToolSpy()
    run = runtime.execute_invoice(IntentSpec.model_validate(payload), spy)
    assert run.gate_a.decision is Decision.APPROVE
    assert run.runtime_decision.reason_codes == ("RUNTIME_AMOUNT_OUTSIDE_CONTRACT",)
    assert not any(tool == "stage_payment" for tool, _ in spy.calls)


def test_integrated_controller_intercepts_mutated_proposal(monkeypatch):
    original = runtime._propose
    def propose(run, tool):
        proposal = original(run, tool)
        if tool == "stage_payment":
            proposal["arguments"]["amount"] = "1000000"
        return proposal
    monkeypatch.setattr(runtime, "_propose", propose)
    spy = ToolSpy()
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, spy)
    assert len(spy.calls) == 5
    assert run.state is RunState.REJECTED
    assert run.runtime_decision.reason_codes == ("RUNTIME_AMOUNT_OUTSIDE_CONTRACT",)


def test_mutable_source_cannot_change_evaluated_recorded_or_dispatched_action(approved_trace, monkeypatch):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    original = runtime.decide_runtime
    def decide_then_mutate(state, snapshot):
        decision = original(state, snapshot)
        proposal["arguments"]["amount"] = "999999"
        state.proposed_action = proposal
        return decision
    monkeypatch.setattr(runtime, "decide_runtime", decide_then_mutate)
    spy = ToolSpy()
    runtime._dispatch(run, spy, proposal)
    assert spy.calls == [("stage_payment", {
        "invoice_id": "INV-1001", "purchase_order_id": "PO-1001",
        "amount": "7500.00", "currency": "USD",
    })]
    check, start = run.events[-3:-1]
    assert check.metadata["proposal"] == start.metadata["proposal"]
    assert check.metadata["proposal"]["arguments"]["amount"] == "7500.00"
    assert run.proposed_action == check.metadata["proposal"]


def test_standalone_prior_decision_cannot_be_overwritten_to_resume(approved_trace):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    run.runtime_decision = decide_runtime(run, proposal).model_copy(update={"decision": Decision.REJECT})
    assert_blocked(run, proposal, "RUNTIME_PRIOR_CONTROL_STOP")


def test_pending_clarification_stops_without_acquiring_information(approved_trace):
    run = before_tool(approved_trace)
    run.pending_questions = ("Confirm current invoice evidence",)
    assert_blocked(run, runtime._propose(run, "stage_payment"),
                   "RUNTIME_CLARIFICATION_PENDING", Decision.CLARIFY)


def test_preexisting_approve_is_not_used_as_a_capability(approved_trace):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "stage_payment")
    run.runtime_decision = decide_runtime(run, proposal)
    proposal["arguments"]["amount"] = "999999"
    assert_blocked(run, proposal, "RUNTIME_AMOUNT_OUTSIDE_CONTRACT")


def test_completed_run_cannot_dispatch_again(approved_trace):
    run = ExecutionRun.model_validate(approved_trace)
    original = run.model_dump_json()
    spy = ToolSpy()
    proposal = runtime._propose(run, "stage_payment")
    assert decide_runtime(run, proposal).decision is Decision.REJECT
    with pytest.raises(ValueError, match="running"):
        runtime._dispatch(run, spy, proposal)
    assert run.model_dump_json() == original
    assert spy.calls == []


def test_clearing_evidence_cannot_repeat_an_executed_action(approved_trace):
    run = before_tool(approved_trace)
    proposal = runtime._propose(run, "inspect_invoice")
    assert_blocked(run, proposal, "RUNTIME_ACTION_REPLAY")
