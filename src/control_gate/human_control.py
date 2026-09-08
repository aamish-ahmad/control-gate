"""Bounded local human decisions. No persistence, authentication service or recovery."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from control_gate.contracts import HumanAction, HumanIntervention, IntentSpec, ExecutionRun


SCOPE_KEYS = ("invoice_id", "supplier_id", "purchase_order_id", "amount", "currency")


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def intent_digest(intent: IntentSpec) -> str:
    return digest(intent.model_dump(mode="json"))


def scope(intent: IntentSpec) -> dict[str, object]:
    return {key: intent.inputs.get(key) for key in SCOPE_KEYS}


def scoped_approval(approval: HumanIntervention | None, action: Mapping[str, object]) -> bool:
    """C1's additional guard: a manager may approve only this exact local action."""
    if (approval is None or approval.action is not HumanAction.APPROVE
            or approval.actor_role != "finance_manager" or not approval.actor_id.strip()
            or not approval.reason.strip() or approval.timestamp.utcoffset() is None):
        return False
    changes = approval.constraint_changes
    if set(changes) != {"intent_digest", "approved_action"} or not changes.get("intent_digest"):
        return False
    approved = changes["approved_action"]
    if not isinstance(approved, Mapping) or set(approved) != set(SCOPE_KEYS):
        return False
    if any(approved[key] != action.get(key) for key in SCOPE_KEYS if key != "amount"):
        return False
    try:
        amount = Decimal(str(approved["amount"]))
        return amount.is_finite() and amount > 0 and amount == Decimal(str(action.get("amount")))
    except (InvalidOperation, ValueError):
        return False


def approved_run(run: ExecutionRun) -> bool:
    approval = run.human_approval
    if (approval is None or run.intent_spec is None or run.parent_run_id != approval.run_id
            or approval.intent_id != run.intent_id or approval.intent_version + 1 != run.intent_version):
        return False
    original = run.intent_spec.model_dump(mode="json")
    original["version"] -= 1
    return (approval.constraint_changes.get("intent_digest") == digest(original)
            and scoped_approval(approval, scope(run.intent_spec)))


def changed_intent(run: ExecutionRun, intervention: HumanIntervention) -> IntentSpec:
    """Fill missing inputs or narrow existing constraints; never invent authority."""
    # Reuse Gate B's exact permission adapter after module initialization.
    from control_gate.runtime_admissibility import TOOL_PERMISSIONS
    changes = intervention.model_dump(mode="json")["constraint_changes"]
    if not set(changes) <= {"intent_digest", "inputs", "constraints", "allowed_tools",
                            "prohibited_actions", "reacquire_evidence"}:
        raise ValueError("Unsupported human constraint change")
    original = run.intent_spec.model_dump(mode="json")
    updated = run.intent_spec.model_dump(mode="json")
    for field in ("inputs", "constraints"):
        if field in changes and not isinstance(changes[field], dict):
            raise ValueError("Changes must be typed objects")
    for key, value in changes.get("inputs", {}).items():
        if key not in SCOPE_KEYS or original["inputs"].get(key) not in (None, "") or value in (None, ""):
            raise ValueError("Clarification may only fill missing invoice inputs")
        if key == "amount":
            try:
                parsed = Decimal(str(value))
                if isinstance(value, bool) or not parsed.is_finite() or parsed <= 0:
                    raise ValueError("Amount must be finite and positive")
            except InvalidOperation as error:
                raise ValueError("Invalid amount") from error
        elif (not isinstance(value, str) or not value.strip() or value != value.strip()
                or (key == "currency" and value != "USD")):
            raise ValueError("A canonical nonblank invoice input is required")
        updated["inputs"][key] = value
    for key, value in changes.get("constraints", {}).items():
        previous = original["constraints"].get(key)
        if key == "max_autonomous_payment_usd":
            try:
                amount = Decimal(str(value))
                if isinstance(value, bool) or not amount.is_finite() or amount <= 0 or (previous is not None and amount > Decimal(str(previous))):
                    raise ValueError("Cannot widen autonomous authority")
            except InvalidOperation as error:
                raise ValueError("Invalid cap") from error
        elif key != "currency" or value != "USD" or previous not in (None, "", value):
            raise ValueError("Unsupported or widening constraint")
        if key != "max_autonomous_payment_usd" or previous is None or Decimal(str(previous)) != amount:
            updated["constraints"][key] = value
    if "allowed_tools" in changes:
        allowed = changes["allowed_tools"]
        if not isinstance(allowed, list) or not all(isinstance(v, str) for v in allowed) or not set(allowed) <= set(original["permissions"]["allowed_tools"]):
            raise ValueError("Cannot widen tool permissions")
        if set(allowed) != set(original["permissions"]["allowed_tools"]):
            updated["permissions"]["allowed_tools"] = allowed
    if "prohibited_actions" in changes:
        prohibited = changes["prohibited_actions"]
        if not isinstance(prohibited, list) or not all(isinstance(v, str) and v.strip() for v in prohibited) or not set(original["prohibited_actions"]) <= set(prohibited):
            raise ValueError("Cannot remove prohibitions")
        canonical = set(TOOL_PERMISSIONS) | set(TOOL_PERMISSIONS.values()) | {run.objective, "submit_payment"}
        if not set(prohibited) - set(original["prohibited_actions"]) <= canonical:
            raise ValueError("New prohibitions must constrain an enforced operation")
        if set(prohibited) != set(original["prohibited_actions"]):
            updated["prohibited_actions"] = prohibited
    reacquire = changes.get("reacquire_evidence", [])
    if "reacquire_evidence" in changes and (not isinstance(reacquire, list)
            or not reacquire or not all(isinstance(v, str) for v in reacquire)):
        raise ValueError("Missing evidence names must be a nonempty list")
    if reacquire:
        if (not isinstance(reacquire, list) or run.runtime_decision is None
                or run.runtime_decision.reason_codes != ("RUNTIME_EVIDENCE_MISSING",)
                or run.execution_plan is None):
            raise ValueError("Evidence acquisition requires an existing missing-evidence pause")
        steps = [s.step_id for s in run.execution_plan.steps]
        proposed_tool = (run.proposed_action or {}).get("tool")
        if proposed_tool not in steps:
            raise ValueError("Missing-evidence pause must identify its blocked action")
        missing = set(steps[:steps.index(proposed_tool)]) - set(run.evidence)
        if not set(reacquire) <= missing:
            raise ValueError("Only missing evidence can be requested")
    def executable_tools(data: dict) -> set[str]:
        prohibited = set(data["prohibited_actions"])
        return {tool for tool, permission in TOOL_PERMISSIONS.items()
            if permission in data["permissions"]["allowed_tools"]
            and not {tool, permission, data["goal"]["type"]} & prohibited
            and not (tool == "stage_payment" and ("submit_payment" in prohibited
                or "do_not_submit_payment" in data["requirements"]))}

    authority_changed = executable_tools(updated) != executable_tools(original)
    other_changes = {key: value for key, value in updated.items()
                     if key not in ("permissions", "prohibited_actions")}
    original_other = {key: value for key, value in original.items()
                      if key not in ("permissions", "prohibited_actions")}
    if other_changes == original_other and not authority_changed and not reacquire:
        raise ValueError("Clarification must change executable state")
    updated["version"] += 1
    return IntentSpec.model_validate(updated)
