"""Deterministic C3 Gate B for the existing, fixed supplier-invoice plan."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from pydantic import ValidationError

from control_gate.contracts import (
    FINANCE_V1_POLICY, Decision, EventType, ExecutionRun, PolicySet, RuntimeDecision, RunState,
)
from control_gate.tool_environment import (
    DuplicateCheckResult, InvoiceRecord, PurchaseOrderRecord, SupplierRecord,
)
from control_gate.validation import AUTHORIZED_REQUEST_ROLES, FROZEN_ACTIONS, UNSAFE_ASSUMPTIONS
from control_gate.human_control import approved_run


# Adapt the frozen V1 permission vocabulary to C1 implementations. Duplicate
# and policy reads are bounded invoice-validation dependencies of invoice.parse.
TOOL_PERMISSIONS = {
    "inspect_invoice": "invoice.parse",
    "lookup_supplier": "vendor.lookup",
    "lookup_purchase_order": "po.lookup",
    "check_duplicate": "invoice.parse",
    "retrieve_policy": "invoice.parse",
    "stage_payment": "payment.submit",
}
INVOICE_TOOLS = tuple(TOOL_PERMISSIONS)
_ARGUMENTS = {
    "inspect_invoice": {"invoice_id"}, "lookup_supplier": {"supplier_id"},
    "lookup_purchase_order": {"purchase_order_id"}, "check_duplicate": {"invoice_id"},
    "retrieve_policy": {"policy_version"},
    "stage_payment": {"invoice_id", "purchase_order_id", "amount", "currency"},
}
_EVIDENCE_MODELS = dict(zip(INVOICE_TOOLS, (
    InvoiceRecord, SupplierRecord, PurchaseOrderRecord, DuplicateCheckResult, PolicySet,
)))
_PROPOSAL_FIELDS = {
    "action_id", "run_id", "intent_id", "intent_version", "plan_id", "goal",
    "actor_id", "actor_role", "assumptions", "tool", "arguments",
}


def _amount(value: object) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
        return parsed if parsed.is_finite() and parsed > 0 else None
    except InvalidOperation:
        return None


def _evidence_problem(run: ExecutionRun, required: tuple[str, ...]) -> str | None:
    """Validate successful evidence plus every earlier failed/retried attempt."""
    if not set(required) <= set(run.evidence):
        return "RUNTIME_EVIDENCE_MISSING"
    if set(run.evidence) != set(required):
        return "RUNTIME_ACTION_REPLAY"
    history = list(run.tool_history)
    if (len(history) != len(set(history)) or any(
            action_id != f"{run.run_id}:action:{index}"
            for index, action_id in enumerate(history))):
        return "RUNTIME_ACTION_REPLAY"
    history_set = set(history)
    for event in run.events:
        if event.event_type not in {
                EventType.RUNTIME_POLICY_CHECK, EventType.TOOL_CALL_STARTED,
                EventType.TOOL_CALL_COMPLETED, EventType.TOOL_CALL_FAILED}:
            continue
        action_id = event.metadata.get("action_id")
        if action_id not in history_set:
            return ("RUNTIME_PRIOR_TOOL_FAILURE" if event.event_type is EventType.TOOL_CALL_FAILED
                    else "RUNTIME_EVIDENCE_INVALID")
    evidence = run.model_dump(mode="json", include={"evidence"})["evidence"]
    completed_tools: list[str] = []
    consecutive_failures = 0
    for index, action_id in enumerate(history):
        checks = [e for e in run.events if e.event_type is EventType.RUNTIME_POLICY_CHECK
                  and e.metadata.get("action_id") == action_id]
        starts = [e for e in run.events if e.event_type is EventType.TOOL_CALL_STARTED
                  and e.metadata.get("action_id") == action_id]
        completed = [e for e in run.events if e.event_type is EventType.TOOL_CALL_COMPLETED
                and e.metadata.get("action_id") == action_id]
        failed = [e for e in run.events if e.event_type is EventType.TOOL_CALL_FAILED
                  and e.metadata.get("action_id") == action_id]
        observations = [o for o in run.observations if o.get("action_id") == action_id]
        if not (len(checks) == len(starts) == len(observations) == 1
                and len(completed) + len(failed) == 1):
            return "RUNTIME_EVIDENCE_INVALID"
        check, start, observation = checks[0], starts[0], observations[0]
        end = (completed or failed)[0]
        if len(completed_tools) >= len(INVOICE_TOOLS):
            return "RUNTIME_ACTION_REPLAY"
        tool = INVOICE_TOOLS[len(completed_tools)]
        if (check.decision != Decision.APPROVE.value
                or not check.sequence_number < start.sequence_number < end.sequence_number
                or any(e.tool != tool for e in (check, start, end))
                or observation.get("tool") != tool
                or check.metadata.get("proposal") != start.metadata.get("proposal")
                or check.metadata.get("runtime_decision") != start.metadata.get("runtime_decision")):
            return "RUNTIME_EVIDENCE_INVALID"
        schedules = [e for e in run.events if e.event_type is EventType.RETRY_SCHEDULED
                     and e.metadata.get("failed_action_id") == action_id]
        if completed:
            if (schedules or tool not in evidence
                    or observation.get("output") != run.evidence[tool]
                    or end.metadata.get("observation") != run.evidence[tool]):
                return "RUNTIME_EVIDENCE_INVALID"
            try:
                _EVIDENCE_MODELS[tool].model_validate(evidence[tool])
            except (ValidationError, TypeError):
                return "RUNTIME_EVIDENCE_INVALID"
            completed_tools.append(tool)
            consecutive_failures = 0
            continue
        consecutive_failures += 1
        step = run.execution_plan.steps[len(completed_tools)]
        rule = step.retry_rule
        reasons = observation.get("reason_codes")
        if (len(schedules) != 1 or rule is None or not isinstance(reasons, (tuple, list))
                or len(reasons) != 1 or reasons[0] not in rule.retryable_conditions
                or end.metadata != observation or consecutive_failures > rule.max_retries):
            return "RUNTIME_PRIOR_TOOL_FAILURE"
        schedule = schedules[0]
        if (not end.sequence_number < schedule.sequence_number
                or schedule.tool != tool or schedule.retry_count != consecutive_failures
                or tuple(schedule.metadata.get("reason_codes", ())) != tuple(reasons)
                or schedule.metadata.get("max_retries") != rule.max_retries
                or schedule.metadata.get("next_action_id") !=
                    f"{run.run_id}:action:{index + 1}"):
            return "RUNTIME_PRIOR_TOOL_FAILURE"
    if tuple(completed_tools) != required:
        return "RUNTIME_EVIDENCE_INVALID"
    return None


def _retry_problem(run: ExecutionRun, tool: str) -> str | None:
    """Accept only the live retry state derived from the last recorded failure."""
    state = run.model_dump(mode="json", include={"retry_state"})["retry_state"]
    if state == {"attempts": 0}:
        if run.tool_history:
            last = run.tool_history[-1]
            if any(e.event_type is EventType.TOOL_CALL_FAILED
                   and e.metadata.get("action_id") == last for e in run.events):
                return "RUNTIME_PRIOR_TOOL_FAILURE"
        return None
    if set(state) != {"attempts", "tool", "last_error", "failed_action_id", "max_retries"}:
        return "RUNTIME_RETRY_NOT_AUTHORIZED"
    attempts = state["attempts"]
    step = next((step for step in run.execution_plan.steps if step.step_id == tool), None)
    rule = step.retry_rule if step else None
    if (isinstance(attempts, bool) or not isinstance(attempts, int) or attempts < 1
            or state["tool"] != tool or rule is None
            or state["last_error"] not in rule.retryable_conditions
            or state["max_retries"] != rule.max_retries or attempts > rule.max_retries
            or not run.tool_history or state["failed_action_id"] != run.tool_history[-1]):
        return "RUNTIME_RETRY_NOT_AUTHORIZED"
    action_id = run.tool_history[-1]
    failures = [e for e in run.events if e.event_type is EventType.TOOL_CALL_FAILED
                and e.metadata.get("action_id") == action_id]
    schedules = [e for e in run.events if e.event_type is EventType.RETRY_SCHEDULED
                 and e.metadata.get("failed_action_id") == action_id]
    if (len(failures) != 1 or len(schedules) != 1 or run.events[-1] != schedules[0]
            or schedules[0].retry_count != attempts
            or tuple(schedules[0].metadata.get("reason_codes", ())) != (state["last_error"],)
            or schedules[0].metadata.get("next_action_id") !=
                f"{run.run_id}:action:{len(run.tool_history)}"):
        return "RUNTIME_RETRY_NOT_AUTHORIZED"
    consecutive = 0
    for prior_id in reversed(run.tool_history):
        if any(e.event_type is EventType.TOOL_CALL_FAILED and e.tool == tool
               and e.metadata.get("action_id") == prior_id for e in run.events):
            consecutive += 1
        else:
            break
    return None if consecutive == attempts else "RUNTIME_RETRY_NOT_AUTHORIZED"


def decide_runtime(run: ExecutionRun, proposal: Mapping[str, object]) -> RuntimeDecision:
    """Evaluate current state afresh without tools, mutation, or human/retry effects."""
    expected_id = f"{run.run_id}:action:{len(run.tool_history)}"
    action_id = proposal.get("action_id")
    if not isinstance(action_id, str) or not action_id:
        action_id = expected_id

    def result(code: str, decision: Decision = Decision.REJECT) -> RuntimeDecision:
        return RuntimeDecision(
            run_id=run.run_id, intent_id=run.intent_id, intent_version=run.intent_version,
            plan_id=run.plan_id, action_id=action_id, decision=decision, reason_codes=(code,),
        )

    intent, plan = run.intent_spec, run.execution_plan
    human_approved = approved_run(run)
    if (run.state is not RunState.RUNNING or run.final_outcome is not None
            or intent is None or plan is None or run.gate_a is None
            or (run.gate_a.decision is not Decision.APPROVE and not (
                human_approved and run.gate_a.decision is Decision.ESCALATE
                and set(run.gate_a.reason_codes) <= {
                    "PAYMENT_ABOVE_AUTONOMOUS_LIMIT", "FINANCE_MANAGER_APPROVAL_REQUIRED"}))):
        return result("RUNTIME_NOT_AUTHORIZED")
    if set(proposal) != _PROPOSAL_FIELDS:
        return result("RUNTIME_PROPOSAL_INVALID")
    if (proposal["action_id"] != expected_id
            or any(proposal[key] != getattr(run, key) for key in
                   ("run_id", "intent_id", "intent_version", "plan_id"))):
        return result("RUNTIME_LINKAGE_MISMATCH")
    if (proposal["goal"] != intent.goal.type or intent.goal.type not in FROZEN_ACTIONS
            or run.objective != intent.goal.type):
        return result("RUNTIME_SCOPE_VIOLATION")
    if (proposal["actor_id"] != intent.actor.id or proposal["actor_role"] != intent.actor.role
            or intent.actor.role not in AUTHORIZED_REQUEST_ROLES):
        return result("RUNTIME_ACTOR_UNAUTHORIZED")
    assumptions = proposal["assumptions"]
    if (not isinstance(assumptions, (tuple, list))
            or tuple(assumptions) != intent.assumptions
            or any(a in UNSAFE_ASSUMPTIONS for a in intent.assumptions)):
        return result("RUNTIME_UNSAFE_ASSUMPTION")
    tool = proposal["tool"]
    if not isinstance(tool, str) or tool not in TOOL_PERMISSIONS:
        return result("RUNTIME_TOOL_PROHIBITED")
    permission = TOOL_PERMISSIONS[tool]
    if (tool in intent.prohibited_actions or permission in intent.prohibited_actions
            or intent.goal.type in intent.prohibited_actions
            or (tool == "stage_payment" and "submit_payment" in intent.prohibited_actions)
            or (tool == "stage_payment" and "do_not_submit_payment" in intent.requirements)):
        return result("RUNTIME_TOOL_PROHIBITED")
    if permission not in intent.permissions.allowed_tools:
        return result("RUNTIME_TOOL_UNAUTHORIZED")
    args = proposal["arguments"]
    if not isinstance(args, Mapping) or set(args) != _ARGUMENTS[tool]:
        return result("RUNTIME_ARGUMENTS_INVALID")
    inputs = intent.inputs
    for key in ("invoice_id", "supplier_id", "purchase_order_id", "currency"):
        if key in args and args[key] != inputs.get(key):
            return result("RUNTIME_RESOURCE_UNAUTHORIZED")
    if tool == "retrieve_policy" and args["policy_version"] != run.gate_a.policy_version:
        return result("RUNTIME_RESOURCE_UNAUTHORIZED")
    if ((run.runtime_decision is not None and run.runtime_decision.decision is not Decision.APPROVE)
            or any(e.event_type is EventType.RUNTIME_POLICY_CHECK and e.decision != "APPROVE"
                   for e in run.events)):
        return result("RUNTIME_PRIOR_CONTROL_STOP")
    if run.pending_questions:
        return result("RUNTIME_CLARIFICATION_PENDING", Decision.CLARIFY)
    # A status string alone never conveys authority. C4's immutable scoped
    # decision is checked afresh; unrecognized human events still stop dispatch.
    if (run.approval_state != "NOT_REQUESTED" and not (
            human_approved and run.approval_state == "APPROVED_BY_HUMAN")) or any(
            e.event_type in (EventType.HUMAN_INTERVENTION, EventType.HUMAN_APPROVAL_REQUESTED)
            for e in run.events):
        return result("RUNTIME_HUMAN_AUTHORITY_REQUIRED", Decision.ESCALATE)
    if (tuple(s.step_id for s in plan.steps) != INVOICE_TOOLS
            or any(s.tool_requirements != (s.step_id,)
                   or s.dependencies != ((INVOICE_TOOLS[i - 1],) if i else ())
                   or s.policy_checkpoints or s.approval_checkpoints
                   or s.retry_rule is None
                   or s.retry_rule.max_retries != (0 if s.step_id == "stage_payment"
                       else FINANCE_V1_POLICY.transient_read_max_retries)
                   or s.retry_rule.retryable_conditions != (() if s.step_id == "stage_payment"
                       else ("TOOL_TIMEOUT", "MALFORMED_TOOL_RESPONSE"))
                   for i, s in enumerate(plan.steps))):
        return result("RUNTIME_PLAN_MISMATCH")
    retry_problem = _retry_problem(run, tool)
    if retry_problem:
        return result(retry_problem)
    required = INVOICE_TOOLS[:INVOICE_TOOLS.index(tool)]
    problem = _evidence_problem(run, required)
    if problem:
        return result(problem, Decision.CLARIFY if problem == "RUNTIME_EVIDENCE_MISSING"
                      else Decision.REJECT)
    if tool != "stage_payment":
        return result("RUNTIME_ACTION_ADMISSIBLE", Decision.APPROVE)

    amount, authorized = _amount(args["amount"]), _amount(inputs.get("amount"))
    cap = _amount(intent.constraints.get("max_autonomous_payment_usd"))
    if amount is None or authorized is None or cap is None:
        return result("RUNTIME_AMOUNT_INVALID")
    if amount != authorized or (amount > cap and not human_approved):
        return result("RUNTIME_AMOUNT_OUTSIDE_CONTRACT")
    if args["currency"] != intent.constraints.get("currency"):
        return result("RUNTIME_CURRENCY_OUTSIDE_CONTRACT")
    invoice = run.evidence["inspect_invoice"]
    supplier = run.evidence["lookup_supplier"]
    po = run.evidence["lookup_purchase_order"]
    duplicate = run.evidence["check_duplicate"]
    if (invoice["invoice_id"] != inputs["invoice_id"]
            or invoice["supplier_id"] != inputs["supplier_id"]
            or invoice["purchase_order_id"] != inputs["purchase_order_id"]
            or supplier["supplier_id"] != inputs["supplier_id"]
            or po["purchase_order_id"] != inputs["purchase_order_id"]
            or po["supplier_id"] != inputs["supplier_id"]
            or duplicate["invoice_id"] != inputs["invoice_id"]):
        return result("RUNTIME_EVIDENCE_CONTRADICTION")
    if not supplier["active"]:
        return result("INACTIVE_SUPPLIER")
    if (po["status"] != "OPEN" or invoice["status"] != "VALIDATED"
            or not invoice["validations_complete"]):
        return result("RUNTIME_VALIDATIONS_INCOMPLETE")
    if duplicate["is_duplicate"]:
        return result("DUPLICATE_INVOICE")
    if amount != _amount(invoice["amount"]) or amount > Decimal(po["remaining_amount"]):
        return result("AMOUNT_MISMATCH")
    if (args["currency"] != invoice["currency"] or args["currency"] != po["currency"]
            or args["currency"] not in supplier["approved_currencies"]):
        return result("RUNTIME_EVIDENCE_CONTRADICTION")
    # The C1 environment stages only against the frozen finance-v1 policy. A
    # changed observed policy cannot silently widen the authorizing policy.
    if run.model_dump(mode="json", include={"evidence"})["evidence"]["retrieve_policy"] != FINANCE_V1_POLICY.model_dump(mode="json"):
        return result("RUNTIME_POLICY_MISMATCH")
    if not human_approved and (amount > FINANCE_V1_POLICY.max_autonomous_payment_usd or any(
            rule.when.strip().lower() == "always" for rule in intent.approval_rules)):
        return result("RUNTIME_APPROVAL_REQUIRED", Decision.ESCALATE)
    return result("RUNTIME_ACTION_ADMISSIBLE", Decision.APPROVE)
