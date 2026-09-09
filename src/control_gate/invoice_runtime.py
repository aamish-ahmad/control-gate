"""Governed invoice trajectory with human control and bounded read recovery."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import TypedDict
from uuid import uuid4
from weakref import ref

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from control_gate.admissibility import decide
from control_gate.contracts import (
    FINANCE_V1_POLICY, Decision, EventType, ExecutionPlan, ExecutionRun, IntentSpec, PlanStep,
    PolicySet, RetryRule, RunOutcome, RunState, TrajectoryEvent, HumanAction, HumanIntervention,
)
from control_gate.evaluation import compile_request
from control_gate.runtime_admissibility import INVOICE_TOOLS, decide_runtime
from control_gate.human_control import approved_run, changed_intent, intent_digest, scope, scoped_approval
from control_gate.tool_environment import (
    DuplicateCheckResult, InvoiceRecord, LocalToolError, PurchaseOrderRecord,
    RetryableLocalToolError, StagedPayment, SupplierInvoiceToolEnvironment, SupplierRecord,
    build_local_tool_environment,
)


DEMO_REQUEST = (
    "finance_agent process invoice INV-1001 from supplier SUP-1001 under PO-1001 "
    "for USD 7500.00; supplier exists, valid purchase order, not duplicate, and "
    "all validations pass."
)
_TOOLS = INVOICE_TOOLS
_RESULT_TYPES = {
    "inspect_invoice": InvoiceRecord, "lookup_supplier": SupplierRecord,
    "lookup_purchase_order": PurchaseOrderRecord, "check_duplicate": DuplicateCheckResult,
    "retrieve_policy": PolicySet, "stage_payment": StagedPayment,
}


class _GraphState(TypedDict):
    run: ExecutionRun


class _PauseContext(dict):
    def __deepcopy__(self, memo: dict) -> _PauseContext:
        # A copied run shares this consumed capability but never its owner
        # identity. Do not copy the retained tool environment or its effects.
        return self


class _MalformedToolResponse(ValueError):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _event(run: ExecutionRun, event_type: EventType, *, before: RunState | None = None,
           tool: str | None = None, status: str = "completed", actor: str | None = None,
           **kwargs: object) -> None:
    sequence = len(run.events)
    run.events += (TrajectoryEvent(
        event_id=f"{run.run_id}:event:{sequence}", run_id=run.run_id,
        intent_id=run.intent_id, intent_version=run.intent_version,
        timestamp=_now(), sequence_number=sequence, event_type=event_type,
        state_before=(before or run.state).value, state_after=run.state.value,
        step_id=tool, tool=tool, actor=actor or run.intent_spec.actor.id,
        status=status, **kwargs,
    ),)


def _finish(run: ExecutionRun, *, reason: str | None = None,
            status: RunState = RunState.FAILED) -> None:
    before = run.state
    intent = run.intent_spec
    satisfied: tuple[str, ...] = ()
    if reason is None:
        # The only implemented outcome semantics are the existing compiler's
        # success conditions, evidenced by real C1 staging and its observations.
        invoice = run.evidence.get("inspect_invoice", {})
        staged = run.evidence.get("stage_payment")
        supported = {
            "invoice_validated": invoice.get("validations_complete") is True
                and invoice.get("status") == "VALIDATED",
            "payment_authorized": staged is not None
                and (run.gate_a.decision is Decision.APPROVE or approved_run(run))
                and run.runtime_decision is not None
                and run.runtime_decision.decision is Decision.APPROVE,
            "audit_event_written": any(
                e.event_type is EventType.TOOL_CALL_COMPLETED and e.tool == "stage_payment"
                for e in run.events
            ),
        }
        satisfied = tuple(c for c in intent.success_conditions if supported.get(c, False))
        if len(satisfied) == len(intent.success_conditions):
            status = RunState.COMPLETED
        else:
            reason = "SUCCESS_CONDITIONS_NOT_SATISFIED"
    failure_condition = {
        "DUPLICATE_INVOICE": "duplicate_invoice",
        "INVOICE_PURCHASE_ORDER_MISMATCH": "purchase_order_mismatch",
    }.get(reason)
    run.state = status
    run.final_outcome = RunOutcome(
        outcome_id=f"{run.run_id}:outcome", run_id=run.run_id,
        intent_id=run.intent_id, intent_version=run.intent_version, status=status,
        success_conditions_satisfied=satisfied,
        failure_conditions_triggered=(failure_condition,)
            if failure_condition in intent.failure_conditions else (),
        completed_at=_now(),
        summary=("Local payment staged; supported intent success conditions satisfied. "
                 "No payment submitted and no external actions performed.")
            if reason is None else
            f"Parent consumed by human decision; continuation: {run.continuation_run_id}."
            if reason == "HUMAN_CONTINUATION_CREATED" else
            f"Execution stopped: {reason}. No further automatic retry or continuation.",
    )
    _event(run, EventType.RUN_COMPLETED if status is RunState.COMPLETED else EventType.RUN_FAILED,
           before=before, status=status.value, metadata={
               "plan_id": run.plan_id, "reason_codes": [reason] if reason else [],
               "final_outcome": run.final_outcome.model_dump(mode="json"),
               "external_actions_performed": 0,
           })


def _arguments(run: ExecutionRun, tool: str) -> dict[str, object]:
    inputs = run.intent_spec.inputs
    if tool == "inspect_invoice":
        return {"invoice_id": inputs["invoice_id"]}
    invoice = run.evidence["inspect_invoice"]
    if tool == "lookup_supplier":
        return {"supplier_id": invoice["supplier_id"]}
    if tool == "lookup_purchase_order":
        return {"purchase_order_id": invoice["purchase_order_id"]}
    if tool == "check_duplicate":
        return {"invoice_id": invoice["invoice_id"]}
    if tool == "retrieve_policy":
        return {"policy_version": run.gate_a.policy_version}
    return {
        "invoice_id": invoice["invoice_id"],
        "purchase_order_id": run.evidence["lookup_purchase_order"]["purchase_order_id"],
        "amount": inputs["amount"], "currency": inputs["currency"],
    }


def _propose(run: ExecutionRun, tool: str) -> dict[str, object]:
    return {
        "action_id": f"{run.run_id}:action:{len(run.tool_history)}",
        "run_id": run.run_id, "intent_id": run.intent_id,
        "intent_version": run.intent_version, "plan_id": run.plan_id,
        "goal": run.objective, "actor_id": run.intent_spec.actor.id,
        "actor_role": run.intent_spec.actor.role,
        "assumptions": list(run.intent_spec.assumptions),
        "tool": tool, "arguments": _arguments(run, tool),
    }


def _dispatch(run: ExecutionRun, environment: SupplierInvoiceToolEnvironment,
              proposal: dict[str, object]) -> None:
    """The sole tool boundary: freeze, freshly decide, record, then dispatch."""
    if run.state is not RunState.RUNNING or run.final_outcome is not None:
        raise ValueError("Only a running trajectory can dispatch")
    run.proposed_action = proposal
    snapshot = run.proposed_action
    payload = run.model_dump(mode="json", include={"proposed_action"})["proposed_action"]
    decision = decide_runtime(run, snapshot)
    run.proposed_action = payload
    run.runtime_decision = decision
    tool = snapshot.get("tool")
    event_tool = tool if isinstance(tool, str) and tool else None
    metadata = {"action_id": decision.action_id, "plan_id": run.plan_id,
                "proposal": payload, "runtime_decision": decision.model_dump(mode="json")}
    if run.human_approval is not None:
        metadata["human_approval"] = run.human_approval.model_dump(mode="json")
    _event(run, EventType.RUNTIME_POLICY_CHECK, tool=event_tool,
           decision=decision.decision.value, status=decision.decision.value,
           metadata=metadata)
    if decision.decision is not Decision.APPROVE:
        reason = decision.reason_codes[0]
        if decision.decision is Decision.REJECT:
            _finish(run, reason=reason, status=RunState.REJECTED)
        else:
            # Stop first. Only a separate validated human intervention can
            # consume the pause and authorize a linked continuation.
            before = run.state
            run.state = (RunState.CLARIFICATION_REQUIRED if decision.decision is Decision.CLARIFY
                         else RunState.ESCALATION_REQUIRED)
            if decision.decision is Decision.CLARIFY:
                run.pending_questions = (f"Required execution evidence is missing: {reason}",)
            else:
                run.approval_state = "REQUIRED"
            _event(run, EventType.CONTROL_DECISION, before=before,
                   decision=decision.decision.value, status=run.state.value, metadata=metadata)
        return
    # Dispatch the frozen evaluated arguments, never the caller's mutable dict
    # or a later proposal. No externally supplied decision is accepted here.
    arguments = dict(snapshot["arguments"])
    action_id = decision.action_id
    run.tool_history += (action_id,)
    _event(run, EventType.TOOL_CALL_STARTED, tool=tool,
           tool_input_digest=_digest(arguments), metadata={
               **payload, **metadata,
           })
    started = perf_counter()
    try:
        if tool == "stage_payment" and approved_run(run):
            arguments["approval"] = run.human_approval
        observation = getattr(environment, tool)(**arguments)
        if not isinstance(observation, _RESULT_TYPES[tool]):
            raise _MalformedToolResponse(
                "Local tool did not return its expected contract record")
        output = observation.model_dump(mode="json")
    except (LocalToolError, ValueError, TypeError, TimeoutError, PermissionError) as error:
        reason = (error.code.value if isinstance(error, LocalToolError)
                  else "MALFORMED_TOOL_RESPONSE" if isinstance(error, _MalformedToolResponse)
                  else "PERMISSION_DENIED" if isinstance(error, PermissionError)
                  else "TOOL_EXECUTION_FAILED")
        observed = {"action_id": action_id, "tool": tool,
                    "error_type": type(error).__name__, "reason_codes": [reason]}
        run.observations = (*run.model_dump(mode="json", include={"observations"})["observations"], observed)
        _event(run, EventType.TOOL_CALL_FAILED, tool=tool, status="failed",
                latency_ms=max(0, int((perf_counter() - started) * 1000)), metadata=observed)
        step = next(step for step in run.execution_plan.steps if step.step_id == tool)
        rule = step.retry_rule
        retry = run.retry_state
        attempts = (retry.get("attempts", 0) if retry.get("tool") == tool else 0)
        explicitly_retryable = (isinstance(error, RetryableLocalToolError)
                                or isinstance(error, _MalformedToolResponse))
        if (explicitly_retryable and rule is not None
                and reason in rule.retryable_conditions and attempts < rule.max_retries):
            attempts += 1
            next_action_id = f"{run.run_id}:action:{len(run.tool_history)}"
            run.retry_state = {"attempts": attempts, "tool": tool,
                "last_error": reason, "failed_action_id": action_id,
                "max_retries": rule.max_retries}
            _event(run, EventType.RETRY_SCHEDULED, tool=tool, status="scheduled",
                   retry_count=attempts, metadata={"failed_action_id": action_id,
                       "next_action_id": next_action_id, "reason_codes": [reason],
                       "max_retries": rule.max_retries})
            return
        _finish(run, reason=reason)
        return
    prior = run.model_dump(mode="json", include={"evidence", "observations"})
    run.evidence = {**prior["evidence"], tool: output}
    run.observations = (*prior["observations"],
                        {"action_id": action_id, "tool": tool, "output": output})
    run.retry_state = {"attempts": 0}
    _event(run, EventType.TOOL_CALL_COMPLETED, tool=tool,
           tool_output_digest=_digest(output),
           latency_ms=max(0, int((perf_counter() - started) * 1000)),
           metadata={"action_id": action_id, "plan_id": run.plan_id, "observation": output})
    if tool == "inspect_invoice":
        # Preserve the fixed workflow's target binding; never silently replace
        # requested entities/amount with a different observed invoice.
        inputs = run.intent_spec.inputs
        if (any(output[key] != inputs[key] for key in
                ("invoice_id", "supplier_id", "purchase_order_id", "currency"))
                or Decimal(output["amount"]) != Decimal(str(inputs["amount"]))):
            _finish(run, reason="INVOICE_INPUT_MISMATCH")
    elif tool == "check_duplicate" and output["is_duplicate"]:
        _finish(run, reason="DUPLICATE_INVOICE")


def _advance(run: ExecutionRun, environment: SupplierInvoiceToolEnvironment) -> None:
    if run.state is not RunState.RUNNING or run.final_outcome is not None:
        raise ValueError("Only a running trajectory can advance")
    completed = set(run.evidence)
    step = next((step for step in run.execution_plan.steps
                 if step.step_id not in completed
                 and set(step.dependencies) <= completed), None)
    if step is None:
        _finish(run)
        return
    _dispatch(run, environment, _propose(run, step.tool_requirements[0]))


def execute_invoice(request: str | IntentSpec,
                    environment: SupplierInvoiceToolEnvironment | None = None) -> ExecutionRun:
    """Start from Gate A; only resume_invoice accepts a live human-control pause."""
    if not isinstance(request, (str, IntentSpec)):
        raise TypeError("Expected a request or IntentSpec, never a previous run")
    intent = compile_request(request) if isinstance(request, str) else request
    return _execute(intent, environment if environment is not None else build_local_tool_environment())


def _execute(intent: IntentSpec, local: SupplierInvoiceToolEnvironment, *,
             parent: ExecutionRun | None = None, approval: HumanIntervention | None = None,
             run_id: str | None = None, used_ids: frozenset[str] = frozenset()) -> ExecutionRun:
    gate_a = decide(intent)
    run_id = run_id or f"RUN-{uuid4()}"
    plan_id = f"{run_id}:plan"  # Reserved identity; non-APPROVE never creates a plan.
    approved = gate_a.decision is Decision.APPROVE or (approval is not None
        and gate_a.decision is Decision.ESCALATE and set(gate_a.reason_codes) <= {
            "PAYMENT_ABOVE_AUTONOMOUS_LIMIT", "FINANCE_MANAGER_APPROVAL_REQUIRED"})
    plan = ExecutionPlan(
        plan_id=plan_id, intent_id=intent.intent_id, intent_version=intent.version,
        steps=tuple(PlanStep(
            step_id=tool, dependencies=(_TOOLS[index - 1],) if index else (),
            tool_requirements=(tool,), retry_rule=RetryRule(
                max_retries=(0 if tool == "stage_payment"
                             else FINANCE_V1_POLICY.transient_read_max_retries),
                retryable_conditions=(() if tool == "stage_payment" else
                    ("TOOL_TIMEOUT", "MALFORMED_TOOL_RESPONSE")),
            ),
        ) for index, tool in enumerate(_TOOLS)),
        terminal_success_state=RunState.COMPLETED,
        terminal_failure_states=(RunState.FAILED, RunState.REJECTED),
    ) if approved else None
    run = ExecutionRun(
        run_id=run_id, intent_id=intent.intent_id, intent_version=intent.version,
        plan_id=plan_id, state=RunState.AWAITING_DECISION, objective=intent.goal.type,
        intent_spec=intent, execution_plan=plan, gate_a=gate_a,
        parent_run_id=parent.run_id if parent else None, human_approval=approval,
        pending_questions=gate_a.questions,
        approval_state="APPROVED_BY_HUMAN" if approval else
            "REQUIRED" if gate_a.decision is Decision.ESCALATE else "NOT_REQUESTED",
    )
    before = run.state
    run.state = RunState.APPROVED if approved else {
        Decision.APPROVE: RunState.APPROVED, Decision.CLARIFY: RunState.CLARIFICATION_REQUIRED,
        Decision.ESCALATE: RunState.ESCALATION_REQUIRED, Decision.REJECT: RunState.REJECTED,
    }[gate_a.decision]
    _event(run, EventType.CONTROL_DECISION, before=before,
           decision=gate_a.decision.value, metadata={"gate_a": gate_a.model_dump(mode="json"),
               "human_approval": approval.model_dump(mode="json") if approval else None,
               "parent_run_id": run.parent_run_id})
    if not approved:
        if gate_a.decision is Decision.REJECT:
            _finish(run, reason=gate_a.reason_codes[0], status=RunState.REJECTED)
        _pause(run, local, used_ids)
        return run
    run.state = RunState.PLANNED
    _event(run, EventType.PLAN_CREATED, before=RunState.APPROVED,
           metadata={"plan": plan.model_dump(mode="json")})
    run.state = RunState.RUNNING
    _event(run, EventType.RUN_STARTED, before=RunState.PLANNED,
           metadata={"plan_id": plan_id, "gate_b": "ENFORCED_C3"})

    def advance(state: _GraphState) -> _GraphState:
        _advance(state["run"], local)
        return state

    graph = StateGraph(_GraphState)
    graph.add_node("advance", advance)
    graph.add_edge(START, "advance")
    graph.add_conditional_edges("advance", lambda state:
        "advance" if state["run"].state is RunState.RUNNING else END,
        {"advance": "advance", END: END})
    # Same-episode state only: no persistence, model calls, or external tracing.
    with tracing_context(enabled=False):
        limit = sum(1 + step.retry_rule.max_retries for step in plan.steps) + 3
        result = graph.compile().invoke({"run": run}, {"recursion_limit": limit})
    run = result["run"]
    _pause(run, local, used_ids)
    return run


def _pause(run: ExecutionRun, environment: SupplierInvoiceToolEnvironment,
           used_ids: frozenset[str]) -> None:
    if run.state in (RunState.CLARIFICATION_REQUIRED, RunState.ESCALATION_REQUIRED):
        # A live handle, not a serialization/recovery capability. Copies retain
        # the weak owner pointing to the original and therefore cannot resume.
        run._pause_context = _PauseContext(owner=ref(run), environment=environment,
            digest=_digest(run.model_dump(mode="json")), consumed=False, used_ids=used_ids)


def intervention_request(run: ExecutionRun) -> dict[str, object]:
    """Surface the exact pending decision and reviewed state to a trusted human caller."""
    _live_pause(run)
    return {"run_id": run.run_id, "intent_id": run.intent_id, "intent_version": run.intent_version,
        "state": run.state.value, "intent_digest": intent_digest(run.intent_spec),
        "approved_action": scope(run.intent_spec), "questions": list(run.pending_questions),
        "reason_codes": list((run.runtime_decision or run.gate_a).reason_codes),
        "proposed_action": run.model_dump(mode="json")["proposed_action"],
        "evidence": run.model_dump(mode="json")["evidence"]}


def _live_pause(run: ExecutionRun) -> dict:
    context = run._pause_context
    if (not isinstance(context, dict) or context["owner"]() is not run or context["consumed"]
            or run.state not in (RunState.CLARIFICATION_REQUIRED, RunState.ESCALATION_REQUIRED)
            or run.final_outcome is not None or context["digest"] != _digest(run.model_dump(mode="json"))):
        raise ValueError("A current, unconsumed live human-control pause is required")
    return context


def resume_invoice(run: ExecutionRun, intervention: HumanIntervention) -> ExecutionRun:
    """Consume one explicit human decision; never retry a failed or terminal run.

    The local caller is the trusted human adapter, responsible for actor identity.
    This API supplies no external authentication or durable resume mechanism.
    """
    context = _live_pause(run)
    if not isinstance(intervention, HumanIntervention):
        raise TypeError("A structured HumanIntervention is required")
    if ((intervention.run_id, intervention.intent_id, intervention.intent_version) !=
            (run.run_id, run.intent_id, run.intent_version)
            or intervention.intervention_id in context["used_ids"]
            or not intervention.intervention_id.strip()
            or intervention.timestamp.utcoffset() is None
            or not run.events[-1].timestamp <= intervention.timestamp <= _now()
            or not intervention.actor_id.strip() or not intervention.reason.strip()
            or intervention.actor_role not in {"finance_manager", "accounts_payable_operator"}
            or intervention.constraint_changes.get("intent_digest") != intent_digest(run.intent_spec)):
        raise ValueError("Human decision is stale, unbound or unauthorized")
    action = intervention.action
    if action is HumanAction.APPROVE:
        if (run.state is not RunState.ESCALATION_REQUIRED
                or not scoped_approval(intervention, scope(run.intent_spec))):
            raise ValueError("Explicit finance-manager approval of the exact escalated action is required")
        data = run.intent_spec.model_dump(mode="json")
        data["version"] += 1
        intent = IntentSpec.model_validate(data)
    elif action is HumanAction.MODIFY_CONSTRAINT:
        intent = changed_intent(run, intervention)
    elif set(intervention.constraint_changes) != {"intent_digest"}:
        raise ValueError("Deny/cancel cannot change authority")
    child_id = f"RUN-{uuid4()}" if action in (HumanAction.APPROVE, HumanAction.MODIFY_CONSTRAINT) else None
    context["consumed"] = True  # consume before any child tool or observable mutation
    run.continuation_run_id = child_id
    run.approval_state = "CONSUMED_BY_HUMAN" if child_id else action.value
    _event(run, EventType.HUMAN_INTERVENTION, actor=intervention.actor_id,
           decision=action.value, metadata={"intervention": intervention.model_dump(mode="json"),
               "continuation_run_id": child_id})
    _finish(run, reason="HUMAN_DENIED" if action is HumanAction.DENY else
            "HUMAN_CANCELLED" if action is HumanAction.CANCEL else "HUMAN_CONTINUATION_CREATED",
            status=RunState.REJECTED if action is HumanAction.DENY else RunState.CANCELLED)
    if child_id is None:
        return run
    return _execute(intent, context["environment"], parent=run,
                    approval=intervention if action is HumanAction.APPROVE else None,
                    run_id=child_id, used_ids=context["used_ids"] | {intervention.intervention_id})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", default=DEMO_REQUEST)
    args = parser.parse_args()
    run = execute_invoice(args.request)
    print(run.model_dump_json(indent=2))
    return 0 if run.state is RunState.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
