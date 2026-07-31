"""Deterministic static validation for frozen Control Gate V1 intents."""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, JsonValue, ValidationError

from control_gate.contracts import FINANCE_V1_POLICY, IntentSpec


class FindingSeverity(str, Enum):
    """The frozen validator is blocking; decision semantics are applied later."""

    BLOCKING = "BLOCKING"


class FindingCode(str, Enum):
    """Stable codes derived one-for-one from the eleven frozen V1 checks."""

    SCHEMA_INVALID = "V_SCHEMA_INVALID"
    REQUIRED_FIELD_MISSING = "V_REQUIRED_FIELD_MISSING"
    AMBIGUOUS_ENTITY_REFERENCE = "V_AMBIGUOUS_ENTITY_REFERENCE"
    APPROVAL_RULE_MISSING = "V_APPROVAL_RULE_MISSING"
    CONTRADICTORY_REQUIREMENTS = "V_CONTRADICTORY_REQUIREMENTS"
    UNBOUNDED_PERMISSIONS = "V_UNBOUNDED_PERMISSIONS"
    UNKNOWN_OR_DISALLOWED_TOOL = "V_TOOL_UNKNOWN_OR_DISALLOWED"
    UNSAFE_ASSUMPTION = "V_UNSAFE_ASSUMPTION"
    SUCCESS_CONDITION_MISSING = "V_SUCCESS_CONDITIONS_MISSING"
    NON_REVERSIBLE_HIGH_IMPACT_ACTION = "V_NON_REVERSIBLE_HIGH_IMPACT_ACTION"
    POLICY_CONFLICT = "V_POLICY_CONFLICT"


class ValidationFinding(BaseModel):
    """A machine-readable, deterministic explanation of one static issue."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: FindingCode
    severity: FindingSeverity
    field: str
    explanation: str
    evidence: dict[str, JsonValue]
    remediation: str | None = None


FINDING_ORDER = {code: index for index, code in enumerate(FindingCode)}
REQUIRED_INPUT_FIELDS = (
    "invoice_id",
    "supplier_id",
    "purchase_order_id",
    "amount",
    "currency",
)
KNOWN_TOOLS = frozenset(
    {
        "invoice.parse",
        "vendor.lookup",
        "po.lookup",
        "payment.submit",
        "audit.write",
    }
)
FROZEN_ACTIONS = frozenset({"process_supplier_invoice", "submit_payment"})
AUTHORIZED_REQUEST_ROLES = frozenset(
    {"automated_finance_operator", "accounts_payable_operator", "finance_manager"}
)
UNSAFE_ASSUMPTIONS = frozenset(
    {
        "assume_vendor_exists_without_lookup",
        "assume_po_valid_without_lookup",
        "assume_payment_succeeded_without_confirmation",
    }
)
CONTRADICTORY_REQUIREMENT_PAIRS = (
    frozenset({"submit_payment", "do_not_submit_payment"}),
    frozenset({"require_approval", "bypass_approval"}),
)
HIGH_IMPACT_ACTIONS = frozenset({"submit_payment", "vendor.modify_bank_details"})


def _finding(
    code: FindingCode,
    field: str,
    explanation: str,
    evidence: dict[str, JsonValue],
    remediation: str | None,
) -> ValidationFinding:
    return ValidationFinding(
        code=code,
        severity=FindingSeverity.BLOCKING,
        field=field,
        explanation=explanation,
        evidence=evidence,
        remediation=remediation,
    )


def _decimal(value: JsonValue) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _schema_findings(error: ValidationError) -> tuple[ValidationFinding, ...]:
    findings = []
    for detail in sorted(error.errors(), key=lambda item: tuple(map(str, item["loc"]))):
        field = ".".join(map(str, detail["loc"])) or "$"
        findings.append(
            _finding(
                FindingCode.SCHEMA_INVALID,
                field,
                "The candidate does not conform to the frozen IntentSpec schema.",
                {
                    "error_type": str(detail["type"]),
                    "message": str(detail["msg"]),
                },
                "Repair the candidate payload before admissibility is evaluated.",
            )
        )
    return tuple(findings)


def validate_intent(
    candidate: IntentSpec | Mapping[str, Any],
) -> tuple[ValidationFinding, ...]:
    """Run only the eleven static checks frozen for V1, without side effects."""

    if isinstance(candidate, IntentSpec):
        intent = candidate
    else:
        try:
            intent = IntentSpec.model_validate(candidate)
        except ValidationError as error:
            return _schema_findings(error)

    findings: list[ValidationFinding] = []

    if intent.goal.type == "unresolved":
        findings.append(
            _finding(
                FindingCode.REQUIRED_FIELD_MISSING,
                "goal.type",
                "The requested action is materially missing.",
                {"observed": "unresolved"},
                "Clarify the intended frozen supplier-invoice action.",
            )
        )
    if intent.actor.id == "unresolved" or intent.actor.role == "unresolved":
        findings.append(
            _finding(
                FindingCode.REQUIRED_FIELD_MISSING,
                "actor",
                "The requesting actor identity or role is materially missing.",
                {"actor_id": intent.actor.id, "actor_role": intent.actor.role},
                "Provide the requesting actor identity and role.",
            )
        )
    for field in REQUIRED_INPUT_FIELDS:
        if intent.inputs.get(field) is None:
            findings.append(
                _finding(
                    FindingCode.REQUIRED_FIELD_MISSING,
                    f"inputs.{field}",
                    f"Required supplier-invoice field '{field}' is missing.",
                    {"observed": None},
                    f"Provide an unambiguous {field.replace('_', ' ')}.",
                )
            )

    candidates = intent.inputs.get("entity_candidates", {})
    if isinstance(candidates, Mapping):
        for entity, values in sorted(candidates.items()):
            if isinstance(values, (list, tuple)) and len(values) > 1:
                findings.append(
                    _finding(
                        FindingCode.AMBIGUOUS_ENTITY_REFERENCE,
                        f"inputs.{entity}",
                        f"Multiple candidates match the referenced {entity}.",
                        {"candidates": list(values)},
                        f"Select exactly one {entity.replace('_', ' ')}.",
                    )
                )

    amount = _decimal(intent.inputs.get("amount"))
    has_finance_approval = any(
        rule.require == FINANCE_V1_POLICY.required_approver_above_limit
        for rule in intent.approval_rules
    )
    if (
        amount is not None
        and amount > FINANCE_V1_POLICY.max_autonomous_payment_usd
        and not has_finance_approval
    ):
        findings.append(
            _finding(
                FindingCode.APPROVAL_RULE_MISSING,
                "approval_rules",
                "A payment above the autonomous limit lacks a finance-manager rule.",
                {
                    "amount": str(amount),
                    "limit": str(FINANCE_V1_POLICY.max_autonomous_payment_usd),
                    "required_approver": (
                        FINANCE_V1_POLICY.required_approver_above_limit
                    ),
                },
                "Add a finance-manager approval rule for this intent version.",
            )
        )

    requirement_set = set(intent.requirements)
    for pair in CONTRADICTORY_REQUIREMENT_PAIRS:
        if pair <= requirement_set:
            findings.append(
                _finding(
                    FindingCode.CONTRADICTORY_REQUIREMENTS,
                    "requirements",
                    "The intent contains mutually incompatible requirements.",
                    {"requirements": sorted(pair)},
                    "Resolve the contradictory requirements.",
                )
            )
    constraint_currency = intent.constraints.get("currency")
    input_currency = intent.inputs.get("currency")
    if (
        constraint_currency is not None
        and input_currency is not None
        and constraint_currency != input_currency
    ):
        findings.append(
            _finding(
                FindingCode.CONTRADICTORY_REQUIREMENTS,
                "constraints.currency",
                "The constrained currency conflicts with the invoice currency.",
                {
                    "constraint_currency": constraint_currency,
                    "invoice_currency": input_currency,
                },
                "Confirm one currency for the invoice and payment constraint.",
            )
        )
    if intent.inputs.get("amount") is not None and amount is None:
        findings.append(
            _finding(
                FindingCode.CONTRADICTORY_REQUIREMENTS,
                "inputs.amount",
                "The supplied amount is not a valid decimal value.",
                {"amount": intent.inputs.get("amount")},
                "Provide a valid non-negative decimal amount.",
            )
        )
    elif amount is not None and amount < 0:
        findings.append(
            _finding(
                FindingCode.CONTRADICTORY_REQUIREMENTS,
                "inputs.amount",
                "The supplied amount is negative.",
                {"amount": str(amount)},
                "Provide the non-negative invoice amount.",
            )
        )

    permission_scope = intent.constraints.get("permission_scope")
    if "*" in intent.permissions.allowed_tools or permission_scope == "unbounded":
        findings.append(
            _finding(
                FindingCode.UNBOUNDED_PERMISSIONS,
                "permissions.allowed_tools",
                "The requested tool permission is unbounded.",
                {
                    "allowed_tools": list(intent.permissions.allowed_tools),
                    "permission_scope": permission_scope,
                },
                "Replace wildcard or unbounded permission with named frozen tools.",
            )
        )

    for tool in sorted(set(intent.permissions.allowed_tools) - KNOWN_TOOLS):
        findings.append(
            _finding(
                FindingCode.UNKNOWN_OR_DISALLOWED_TOOL,
                "permissions.allowed_tools",
                f"Tool '{tool}' is outside the frozen V1 tool surface.",
                {"tool": tool, "known_tools": sorted(KNOWN_TOOLS)},
                "Remove the tool or select a permitted frozen workflow tool.",
            )
        )

    for assumption in sorted(set(intent.assumptions) & UNSAFE_ASSUMPTIONS):
        findings.append(
            _finding(
                FindingCode.UNSAFE_ASSUMPTION,
                "assumptions",
                f"Unsafe assumption '{assumption}' bypasses required evidence.",
                {"assumption": assumption},
                "Replace the assumption with a governed lookup or confirmation.",
            )
        )

    if not intent.success_conditions:
        findings.append(
            _finding(
                FindingCode.SUCCESS_CONDITION_MISSING,
                "success_conditions",
                "The intent has no observable success condition.",
                {"count": 0},
                "Define at least one observable terminal success condition.",
            )
        )

    reversible = intent.constraints.get("reversible")
    if intent.goal.type in HIGH_IMPACT_ACTIONS and reversible is False:
        findings.append(
            _finding(
                FindingCode.NON_REVERSIBLE_HIGH_IMPACT_ACTION,
                "constraints.reversible",
                "The high-impact action is explicitly non-reversible.",
                {"action": intent.goal.type, "reversible": False},
                "Reject the action or provide a safe reversible boundary.",
            )
        )

    policy_conflicts: list[tuple[str, str, str, JsonValue]] = []
    if intent.goal.type not in FROZEN_ACTIONS and intent.goal.type != "unresolved":
        policy_conflicts.append(
            (
                "FROZEN_WORKFLOW",
                "goal.type",
                "The action is outside governed supplier-invoice processing.",
                intent.goal.type,
            )
        )
    if (
        intent.actor.role not in AUTHORIZED_REQUEST_ROLES
        and intent.actor.role != "unresolved"
    ):
        policy_conflicts.append(
            (
                "ACTOR_AUTHORITY",
                "actor.role",
                "The actor role is not authorized for the frozen workflow.",
                intent.actor.role,
            )
        )
    if intent.inputs.get("supplier_exists") is False:
        policy_conflicts.append(
            ("P1", "inputs.supplier_exists", "The supplier does not exist.", False)
        )
    if intent.goal.type == "vendor.modify_bank_details":
        policy_conflicts.append(
            (
                "P2",
                "goal.type",
                "Agents may not modify supplier bank details.",
                intent.goal.type,
            )
        )
    if intent.inputs.get("purchase_order_valid") is False:
        policy_conflicts.append(
            (
                "P3",
                "inputs.purchase_order_valid",
                "The purchase order is invalid.",
                False,
            )
        )
    if intent.inputs.get("duplicate_invoice") is True:
        policy_conflicts.append(
            (
                "P4",
                "inputs.duplicate_invoice",
                "Duplicate invoices must be rejected.",
                True,
            )
        )
    if intent.inputs.get("policy_bypass_requested") is True:
        policy_conflicts.append(
            (
                "P7",
                "inputs.policy_bypass_requested",
                "The request explicitly attempts to bypass approval.",
                True,
            )
        )
    if intent.inputs.get("payment_validations_complete") is False:
        policy_conflicts.append(
            (
                "P8",
                "inputs.payment_validations_complete",
                "Payment cannot proceed before all validations pass.",
                False,
            )
        )

    for rule, field, explanation, observed in policy_conflicts:
        findings.append(
            _finding(
                FindingCode.POLICY_CONFLICT,
                field,
                explanation,
                {"policy_rule": rule, "observed": observed},
                "Remove the policy conflict or terminate the request.",
            )
        )

    return tuple(
        sorted(
            findings,
            key=lambda item: (FINDING_ORDER[item.code], item.field, item.explanation),
        )
    )
