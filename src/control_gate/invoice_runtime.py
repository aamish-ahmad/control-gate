"""C2: one stateful local invoice trajectory. Gate B and continuation are absent."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from time import perf_counter
from typing import TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph
from langsmith import tracing_context
from control_gate.admissibility import decide
from control_gate.contracts import (
    Decision, EventType, ExecutionPlan, ExecutionRun, IntentSpec, PlanStep,
    PolicySet, RetryRule, RunOutcome, RunState, TrajectoryEvent,
)
from control_gate.evaluation import compile_request
from control_gate.tool_environment import (
    DuplicateCheckResult, InvoiceRecord, LocalToolError, PurchaseOrderRecord,
    StagedPayment, SupplierInvoiceToolEnvironment, SupplierRecord, build_local_tool_environment,
)


DEMO_REQUEST = (
    "finance_agent process invoice INV-1001 from supplier SUP-1001 under PO-1001 "
    "for USD 7500.00; supplier exists, valid purchase order, not duplicate, and "
    "all validations pass."
)
_TOOLS = (
    "inspect_invoice", "lookup_supplier", "lookup_purchase_order",
    "check_duplicate", "retrieve_policy", "stage_payment",
)
_RESULT_TYPES = {
    "inspect_invoice": InvoiceRecord, "lookup_supplier": SupplierRecord,
    "lookup_purchase_order": PurchaseOrderRecord, "check_duplicate": DuplicateCheckResult,
    "retrieve_policy": PolicySet, "stage_payment": StagedPayment,
}


class _GraphState(TypedDict):
    run: ExecutionRun


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _event(run: ExecutionRun, event_type: EventType, *, before: RunState | None = None,
           tool: str | None = None, status: str = "completed", **kwargs: object) -> None:
    sequence = len(run.events)
    run.events += (TrajectoryEvent(
        event_id=f"{run.run_id}:event:{sequence}", run_id=run.run_id,
        intent_id=run.intent_id, intent_version=run.intent_version,
        timestamp=_now(), sequence_number=sequence, event_type=event_type,
        state_before=(before or run.state).value, state_after=run.state.value,
        step_id=tool, tool=tool, actor=run.intent_spec.actor.id,
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
                and run.gate_a.decision is Decision.APPROVE,
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
            if reason is None else f"Execution stopped: {reason}. No retry or continuation.",
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


def _advance(run: ExecutionRun, environment: SupplierInvoiceToolEnvironment) -> None:
    if run.state is not RunState.RUNNING or run.final_outcome is not None:
        raise ValueError("Only a running C2 trajectory can advance")
    completed = set(run.evidence)
    step = next((step for step in run.execution_plan.steps
                 if step.step_id not in completed
                 and set(step.dependencies) <= completed), None)
    if step is None:
        _finish(run)
        return
    tool = step.tool_requirements[0]
    arguments = _arguments(run, tool)
    action_id = f"{run.run_id}:action:{len(run.tool_history)}"
    proposal = {"action_id": action_id, "plan_id": run.plan_id,
                "tool": tool, "arguments": arguments}
    # Frozen JSON validation keeps observable proposals immutable. This is not
    # a RuntimeDecision: C3 will own runtime admissibility at this boundary.
    run.proposed_action = proposal
    run.tool_history += (action_id,)
    _event(run, EventType.TOOL_CALL_STARTED, tool=tool,
           tool_input_digest=_digest(arguments), metadata={
               **proposal, "runtime_decision": None, "gate_b": "NOT_IMPLEMENTED_C2",
           })
    started = perf_counter()
    try:
        observation = getattr(environment, tool)(**arguments)
        if not isinstance(observation, _RESULT_TYPES[tool]):
            raise ValueError("Local tool did not return its expected contract record")
        output = observation.model_dump(mode="json")
    except (LocalToolError, ValueError, TypeError, TimeoutError) as error:
        reason = error.code.value if isinstance(error, LocalToolError) else "TOOL_EXECUTION_FAILED"
        observed = {"action_id": action_id, "tool": tool,
                    "error_type": type(error).__name__, "reason_codes": [reason]}
        run.observations = (*run.model_dump(mode="json", include={"observations"})["observations"], observed)
        _event(run, EventType.TOOL_CALL_FAILED, tool=tool, status="failed",
               latency_ms=max(0, int((perf_counter() - started) * 1000)), metadata=observed)
        _finish(run, reason=reason)
        return
    prior = run.model_dump(mode="json", include={"evidence", "observations"})
    run.evidence = {**prior["evidence"], tool: output}
    run.observations = (*prior["observations"],
                        {"action_id": action_id, "tool": tool, "output": output})
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


def execute_invoice(request: str | IntentSpec,
                    environment: SupplierInvoiceToolEnvironment | None = None) -> ExecutionRun:
    """Run once from Gate A. No API accepts a prior run, override, or resume token."""
    if not isinstance(request, (str, IntentSpec)):
        raise TypeError("Expected a request or IntentSpec, never a previous run")
    intent = compile_request(request) if isinstance(request, str) else request
    gate_a = decide(intent)
    run_id = f"RUN-{uuid4()}"
    plan_id = f"{run_id}:plan"  # Reserved identity; non-APPROVE never creates a plan.
    approved = gate_a.decision is Decision.APPROVE
    plan = ExecutionPlan(
        plan_id=plan_id, intent_id=intent.intent_id, intent_version=intent.version,
        steps=tuple(PlanStep(
            step_id=tool, dependencies=(_TOOLS[index - 1],) if index else (),
            tool_requirements=(tool,), retry_rule=RetryRule(max_retries=0),
        ) for index, tool in enumerate(_TOOLS)),
        terminal_success_state=RunState.COMPLETED,
        terminal_failure_states=(RunState.FAILED, RunState.REJECTED),
    ) if approved else None
    run = ExecutionRun(
        run_id=run_id, intent_id=intent.intent_id, intent_version=intent.version,
        plan_id=plan_id, state=RunState.AWAITING_DECISION, objective=intent.goal.type,
        intent_spec=intent, execution_plan=plan, gate_a=gate_a,
        pending_questions=gate_a.questions,
        approval_state="REQUIRED" if gate_a.decision is Decision.ESCALATE else "NOT_REQUESTED",
    )
    before = run.state
    run.state = {
        Decision.APPROVE: RunState.APPROVED, Decision.CLARIFY: RunState.CLARIFICATION_REQUIRED,
        Decision.ESCALATE: RunState.ESCALATION_REQUIRED, Decision.REJECT: RunState.REJECTED,
    }[gate_a.decision]
    _event(run, EventType.CONTROL_DECISION, before=before,
           decision=gate_a.decision.value, metadata={"gate_a": gate_a.model_dump(mode="json")})
    if not approved:
        if gate_a.decision is Decision.REJECT:
            _finish(run, reason=gate_a.reason_codes[0], status=RunState.REJECTED)
        return run
    run.state = RunState.PLANNED
    _event(run, EventType.PLAN_CREATED, before=RunState.APPROVED,
           metadata={"plan": plan.model_dump(mode="json")})
    run.state = RunState.RUNNING
    _event(run, EventType.RUN_STARTED, before=RunState.PLANNED,
           metadata={"plan_id": plan_id, "gate_b": "NOT_IMPLEMENTED_C2"})
    local = environment if environment is not None else build_local_tool_environment()

    def advance(state: _GraphState) -> _GraphState:
        _advance(state["run"], local)
        return state

    graph = StateGraph(_GraphState)
    graph.add_node("advance", advance)
    graph.add_edge(START, "advance")
    graph.add_conditional_edges("advance", lambda state:
        "advance" if state["run"].state is RunState.RUNNING else END,
        {"advance": "advance", END: END})
    # No persistence, interrupt, retries, model calls, or external tracing.
    with tracing_context(enabled=False):
        result = graph.compile().invoke({"run": run}, {"recursion_limit": len(_TOOLS) + 3})
    return result["run"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", default=DEMO_REQUEST)
    args = parser.parse_args()
    run = execute_invoice(args.request)
    print(run.model_dump_json(indent=2))
    return 0 if run.state is RunState.COMPLETED else 1


if __name__ == "__main__":
    raise SystemExit(main())
