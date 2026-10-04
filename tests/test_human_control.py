"""C4 intervention effects and before-tool adversarial acceptance checks."""

from copy import deepcopy
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from control_gate import invoice_runtime as runtime
from control_gate.contracts import ExecutionRun, HumanIntervention, IntentSpec, RunState
from control_gate.evaluation import compile_request
from control_gate.human_control import intent_digest, scope
from control_gate.tool_environment import build_local_tool_environment, LocalToolError


HIGH = runtime.DEMO_REQUEST.replace("1001", "2001").replace("7500.00", "18400.00")


class Spy:
    def __init__(self):
        self.calls = []
        self.environment = build_local_tool_environment()

    def __getattr__(self, tool):
        def invoke(**kwargs):
            self.calls.append((tool, kwargs))
            return getattr(self.environment, tool)(**kwargs)
        return invoke


def pause(*, missing="amount"):
    data = compile_request(runtime.DEMO_REQUEST).model_dump(mode="json")
    data["inputs"].pop(missing)
    spy = Spy()
    run = runtime.execute_invoice(IntentSpec.model_validate(data), spy)
    assert run.state is RunState.CLARIFICATION_REQUIRED and not spy.calls
    return run, spy


def decision(run, action="APPROVE", changes=None, **overrides):
    data = dict(intervention_id=f"H-{uuid4()}", run_id=run.run_id,
        intent_id=run.intent_id, intent_version=run.intent_version,
        timestamp=datetime.now(timezone.utc), actor_id="human-manager",
        actor_role="finance_manager", action=action, reason="Reviewed this invoice and boundary",
        constraint_changes={"intent_digest": intent_digest(run.intent_spec), **(changes or {})})
    if action == "APPROVE" and changes is None:
        data["constraint_changes"]["approved_action"] = scope(run.intent_spec)
    data.update(overrides)
    return HumanIntervention.model_validate(data)


def test_clarification_changes_inputs_before_real_execution():
    run, spy = pause()
    original = run.intent_spec.model_dump_json()
    child = runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", {"inputs": {"amount": "7500.00"}}))
    assert child.state is RunState.COMPLETED and len(spy.calls) == 6
    assert child.intent_spec.inputs["amount"] == "7500.00"
    assert child.intent_id == run.intent_id and child.intent_version == run.intent_version + 1
    assert child.parent_run_id == run.run_id and run.continuation_run_id == child.run_id
    assert child.plan_id != run.plan_id and run.intent_spec.model_dump_json() == original
    assert run.state is RunState.CANCELLED
    assert run.events[-2].actor == "human-manager"
    assert len(spy.environment.staged_payments) == 1


def test_escalation_explicit_manager_approval_enables_exact_action():
    spy = Spy()
    run = runtime.execute_invoice(HIGH, spy)
    assert run.state is RunState.ESCALATION_REQUIRED and spy.calls == []
    review = runtime.intervention_request(run)
    assert review["reason_codes"] == ["PAYMENT_ABOVE_AUTONOMOUS_LIMIT"]
    assert review["approved_action"]["invoice_id"] == "INV-2001"
    child = runtime.resume_invoice(run, decision(run))
    assert child.state is RunState.COMPLETED and len(spy.calls) == 6
    assert child.gate_a.decision.value == "ESCALATE"  # original Gate A remains honest
    assert child.human_approval is not None
    stage_start = next(e for e in child.events if e.event_type.value == "tool_call_started" and e.tool == "stage_payment")
    assert stage_start.metadata["human_approval"]["intervention_id"] == spy.calls[-1][1]["approval"].intervention_id
    assert str(spy.environment.staged_payments[0].amount) == "18400.00"
    assert ExecutionRun.model_validate_json(child.model_dump_json()).model_dump_json() == child.model_dump_json()


@pytest.mark.parametrize("action,status", [("DENY", RunState.REJECTED), ("CANCEL", RunState.CANCELLED)])
def test_deny_cancel_prevent_all_execution(action, status):
    spy = Spy()
    run = runtime.execute_invoice(HIGH, spy)
    result = runtime.resume_invoice(run, decision(run, action))
    assert result is run and run.state is status and spy.calls == []
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run))


@pytest.mark.parametrize("field,value", [
    ("run_id", "wrong"), ("intent_id", "wrong"), ("intent_version", 999),
    ("actor_role", "finance_agent"), ("actor_role", "accounts_payable_operator"),
    ("actor_id", " "), ("reason", " "),
    ("timestamp", datetime(2000, 1, 1, tzinfo=timezone.utc)),
    ("timestamp", datetime(2099, 1, 1, tzinfo=timezone.utc)),
    ("timestamp", datetime(2026, 1, 1)),
])
def test_invalid_manager_decision_does_not_consume_or_call(field, value):
    spy = Spy()
    run = runtime.execute_invoice(HIGH, spy)
    before = run.model_dump_json()
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run, **{field: value}))
    assert spy.calls == [] and run.model_dump_json() == before


@pytest.mark.parametrize("key,value", [("invoice_id", "INV-1001"), ("supplier_id", "SUP-1001"),
    ("purchase_order_id", "PO-1001"), ("amount", "19000"), ("currency", "EUR")])
def test_approval_is_bound_to_every_action_resource(key, value):
    spy = Spy()
    run = runtime.execute_invoice(HIGH, spy)
    approved = scope(run.intent_spec)
    approved[key] = value
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run, changes={"approved_action": approved}))
    assert spy.calls == []


@pytest.mark.parametrize("copy_kind", ["shallow", "deep", "json"])
def test_copied_and_serialized_pauses_cannot_resume(copy_kind):
    run, spy = pause()
    cloned = (run.model_copy() if copy_kind == "shallow" else deepcopy(run) if copy_kind == "deep"
              else ExecutionRun.model_validate_json(run.model_dump_json()))
    with pytest.raises(ValueError):
        runtime.resume_invoice(cloned, decision(run, "MODIFY_CONSTRAINT", {"inputs": {"amount": "7500"}}))
    assert spy.calls == []


def test_accepted_decision_is_single_use_and_stale_state_is_rejected():
    run, spy = pause()
    response = decision(run, "MODIFY_CONSTRAINT", {"inputs": {"amount": "7500"}})
    runtime.resume_invoice(run, response)
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, response)
    assert len(spy.calls) == 6
    run2, spy2 = pause()
    run2.approval_state = "FORGED"
    with pytest.raises(ValueError):
        runtime.resume_invoice(run2, decision(run2, "MODIFY_CONSTRAINT", {"inputs": {"amount": "7500"}}))
    assert spy2.calls == []


@pytest.mark.parametrize("changes", [
    {}, {"inputs": {}}, {"inputs": []}, {"inputs": {"amount": True}},
    {"inputs": {"amount": "NaN"}}, {"inputs": {"amount": -1}},
    {"inputs": {"amount": {"value": 7500}}},
    {"inputs": {"supplier_id": "SUP-2001"}}, {"actor": {"role": "finance_manager"}},
    {"allowed_tools": ["*"]}, {"allowed_tools": [{}]}, {"prohibited_actions": []},
    {"constraints": {"max_autonomous_payment_usd": 50000}},
    {"constraints": {"currency": "EUR"}}, {"constraints": []},
    {"reacquire_evidence": {}}, {"reacquire_evidence": False},
    {"reacquire_evidence": []}, {"reacquire_evidence": ["inspect_invoice"]},
])
def test_noop_malformed_or_widening_clarification_never_reaches_tools(changes):
    run, spy = pause()
    before = run.model_dump_json()
    with pytest.raises((ValueError, TypeError)):
        runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", changes))
    assert not spy.calls and run.model_dump_json() == before


@pytest.mark.parametrize("value", [True, {}, [], " ", " INV-1001"])
def test_malformed_missing_identifier_is_blocked_before_read(value):
    run, spy = pause(missing="invoice_id")
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", {"inputs": {"invoice_id": value}}))
    assert not spy.calls


@pytest.mark.parametrize("change", [
    {"allowed_tools": ["invoice.parse", "vendor.lookup", "po.lookup"]},
    {"constraints": {"max_autonomous_payment_usd": 5000}},
    {"prohibited_actions": ["modify_vendor_bank_details", "bypass_approval", "stage_payment"]},
])
def test_human_narrowing_changes_trajectory_and_blocks_staging(change):
    run, spy = pause()
    if "prohibited_actions" in change:
        change = {"prohibited_actions": list(run.intent_spec.prohibited_actions) + ["stage_payment"]}
    child = runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT",
        {"inputs": {"amount": "7500"}, **change}))
    assert child.state is RunState.REJECTED
    assert "stage_payment" not in [tool for tool, _ in spy.calls]
    assert spy.environment.staged_payments == ()


def test_approval_cannot_override_gate_b_resource_attack(monkeypatch):
    spy = Spy()
    run = runtime.execute_invoice(HIGH, spy)
    original = runtime._propose
    def attack(state, tool):
        proposal = original(state, tool)
        if tool == "stage_payment":
            proposal["arguments"]["invoice_id"] = "INV-1001"
        return proposal
    monkeypatch.setattr(runtime, "_propose", attack)
    child = runtime.resume_invoice(run, decision(run))
    assert child.state is RunState.REJECTED and len(spy.calls) == 5
    assert not spy.environment.staged_payments


def test_c1_guard_keeps_default_limit_and_rechecks_scope():
    run = runtime.execute_invoice(HIGH)
    approval = decision(run)
    env = build_local_tool_environment()
    args = dict(invoice_id="INV-2001", purchase_order_id="PO-2001", amount="18400", currency="USD")
    with pytest.raises(LocalToolError):
        env.stage_payment(**args)
    forged = approval.model_dump(mode="json")
    forged["constraint_changes"]["approved_action"]["amount"] = "19000"
    with pytest.raises(LocalToolError):
        env.stage_payment(**args, approval=HumanIntervention.model_validate(forged))
    assert not env.staged_payments
    assert env.stage_payment(**args, approval=approval).invoice_id == "INV-2001"


@pytest.mark.parametrize("kind", ["rejected", "failed", "completed"])
def test_terminal_runs_cannot_be_resumed(kind):
    spy = Spy()
    request = runtime.DEMO_REQUEST
    if kind == "rejected":
        request += " bypass approval"
    elif kind == "failed":
        request = request.replace("INV-1001", "INV-9999")
    run = runtime.execute_invoice(request, spy)
    assert run.state in (RunState.REJECTED, RunState.FAILED, RunState.COMPLETED)
    before = len(spy.calls)
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run))
    assert len(spy.calls) == before


@pytest.mark.parametrize("kind", ["tools", "prohibitions", "cap"])
def test_semantically_identical_changes_do_not_count_as_clarification(kind):
    run, spy = pause()
    changes = {
        "tools": {"allowed_tools": list(reversed(run.intent_spec.permissions.allowed_tools))},
        "prohibitions": {"prohibited_actions": list(reversed(run.intent_spec.prohibited_actions))},
        "cap": {"constraints": {"max_autonomous_payment_usd": "10000.00"}},
    }[kind]
    with pytest.raises(ValueError, match="change executable state"):
        runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", changes))
    assert not spy.calls


def test_runtime_missing_evidence_requires_explicit_reacquisition(monkeypatch):
    spy = Spy()
    original = runtime._propose
    injected = False
    def missing(state, tool):
        nonlocal injected
        proposal = original(state, tool)
        if tool == "lookup_supplier" and not injected:
            state.evidence = {}
            injected = True
        return proposal
    monkeypatch.setattr(runtime, "_propose", missing)
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, spy)
    assert run.state is RunState.CLARIFICATION_REQUIRED and len(spy.calls) == 1
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", {"reacquire_evidence": ["retrieve_policy"]}))
    child = runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", {"reacquire_evidence": ["inspect_invoice"]}))
    assert child.state is RunState.COMPLETED and len(spy.calls) == 7
    assert child.evidence["inspect_invoice"]["invoice_id"] == "INV-1001"


def test_intervention_id_cannot_be_reused_on_later_pause():
    run, spy = pause()
    first = decision(run, "MODIFY_CONSTRAINT", {"constraints": {"max_autonomous_payment_usd": 5000}})
    child = runtime.resume_invoice(run, first)
    assert child.state is RunState.CLARIFICATION_REQUIRED
    second = decision(child, "MODIFY_CONSTRAINT", {"inputs": {"amount": "7500"}},
                      intervention_id=first.intervention_id)
    with pytest.raises(ValueError):
        runtime.resume_invoice(child, second)
    assert not spy.calls


def test_reviewed_intent_digest_is_required():
    run, spy = pause()
    wrong = decision(run, "MODIFY_CONSTRAINT", {"intent_digest": "wrong", "inputs": {"amount": "7500"}})
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, wrong)
    assert not spy.calls


@pytest.mark.parametrize("kind", ["unknown_prohibition", "unused_permission", "blocked_alias"])
def test_ineffective_authority_edits_cannot_resume(kind):
    run, spy = pause()
    if kind == "blocked_alias":
        first = decision(run, "MODIFY_CONSTRAINT", {
            "prohibited_actions": list(run.intent_spec.prohibited_actions) + ["stage_payment"]})
        run = runtime.resume_invoice(run, first)
        changes = {"prohibited_actions": list(run.intent_spec.prohibited_actions) + ["payment.submit"]}
    elif kind == "unknown_prohibition":
        changes = {"prohibited_actions": list(run.intent_spec.prohibited_actions) + ["not_a_real_operation"]}
    else:
        changes = {"allowed_tools": [v for v in run.intent_spec.permissions.allowed_tools if v != "audit.write"]}
    with pytest.raises(ValueError):
        runtime.resume_invoice(run, decision(run, "MODIFY_CONSTRAINT", changes))
    assert not spy.calls
