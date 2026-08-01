"""Deterministic pre-execution admissibility decisions for Control Gate V1."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from enum import Enum

from control_gate.contracts import (
    FINANCE_V1_POLICY,
    ControlDecision,
    Decision,
    IntentSpec,
)
from control_gate.validation import FindingCode, ValidationFinding, validate_intent


class ReasonCode(str, Enum):
    """Stable Phase 3 reason codes ordered by deterministic precedence."""

    REQUEST_ADMISSIBLE = "REQUEST_ADMISSIBLE"
    PAYMENT_ABOVE_AUTONOMOUS_LIMIT = "PAYMENT_ABOVE_AUTONOMOUS_LIMIT"
    FINANCE_MANAGER_APPROVAL_REQUIRED = "FINANCE_MANAGER_APPROVAL_REQUIRED"
    REQUIRED_FIELD_MISSING = "REQUIRED_FIELD_MISSING"
    AMBIGUOUS_ENTITY_REFERENCE = "AMBIGUOUS_ENTITY_REFERENCE"
    APPROVAL_RULE_MISSING = "APPROVAL_RULE_MISSING"
    CONTRADICTORY_REQUIREMENTS = "CONTRADICTORY_REQUIREMENTS"
    UNBOUNDED_PERMISSIONS = "UNBOUNDED_PERMISSIONS"
    UNKNOWN_OR_DISALLOWED_TOOL = "UNKNOWN_OR_DISALLOWED_TOOL"
    UNSAFE_ASSUMPTION = "UNSAFE_ASSUMPTION"
    SUCCESS_CONDITION_MISSING = "SUCCESS_CONDITION_MISSING"
    NON_REVERSIBLE_HIGH_IMPACT_ACTION = "NON_REVERSIBLE_HIGH_IMPACT_ACTION"
    VENDOR_NOT_FOUND = "VENDOR_NOT_FOUND"
    VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED = (
        "VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED"
    )
    PURCHASE_ORDER_INVALID = "PURCHASE_ORDER_INVALID"
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    APPROVAL_BYPASS_PROHIBITED = "APPROVAL_BYPASS_PROHIBITED"
    REQUIRED_VALIDATIONS_NOT_PASSED = "REQUIRED_VALIDATIONS_NOT_PASSED"
    ACTOR_UNAUTHORIZED = "ACTOR_UNAUTHORIZED"
    ACTION_OUTSIDE_FROZEN_WORKFLOW = "ACTION_OUTSIDE_FROZEN_WORKFLOW"
    POLICY_CONFLICT = "POLICY_CONFLICT"


REJECT_CODE_ORDER = {
    ReasonCode.VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED: 0,
    ReasonCode.DUPLICATE_INVOICE: 1,
    ReasonCode.APPROVAL_BYPASS_PROHIBITED: 2,
    ReasonCode.VENDOR_NOT_FOUND: 3,
    ReasonCode.PURCHASE_ORDER_INVALID: 4,
    ReasonCode.REQUIRED_VALIDATIONS_NOT_PASSED: 5,
    ReasonCode.ACTOR_UNAUTHORIZED: 6,
    ReasonCode.ACTION_OUTSIDE_FROZEN_WORKFLOW: 7,
    ReasonCode.CONTRADICTORY_REQUIREMENTS: 8,
    ReasonCode.UNBOUNDED_PERMISSIONS: 9,
    ReasonCode.UNKNOWN_OR_DISALLOWED_TOOL: 10,
    ReasonCode.UNSAFE_ASSUMPTION: 11,
    ReasonCode.NON_REVERSIBLE_HIGH_IMPACT_ACTION: 12,
    ReasonCode.POLICY_CONFLICT: 13,
}
CLARIFY_CODE_ORDER = {
    ReasonCode.REQUIRED_FIELD_MISSING: 0,
    ReasonCode.AMBIGUOUS_ENTITY_REFERENCE: 1,
    ReasonCode.APPROVAL_RULE_MISSING: 2,
    ReasonCode.CONTRADICTORY_REQUIREMENTS: 3,
    ReasonCode.UNBOUNDED_PERMISSIONS: 4,
    ReasonCode.SUCCESS_CONDITION_MISSING: 5,
}


def decide(
    intent: IntentSpec,
    findings: tuple[ValidationFinding, ...] | None = None,
) -> ControlDecision:
    """Return one reproducible public decision linked to the immutable intent."""

    findings = validate_intent(intent) if findings is None else findings
    reject_reasons = _reject_reasons(findings)
    blocking_fields = tuple(dict.fromkeys(finding.field for finding in findings))

    if reject_reasons:
        return _decision(
            intent,
            Decision.REJECT,
            (min(reject_reasons, key=REJECT_CODE_ORDER.__getitem__),),
            blocking_fields,
            (),
            None,
        )

    clarify_reasons = _clarify_reasons(findings)
    if clarify_reasons:
        return _decision(
            intent,
            Decision.CLARIFY,
            (min(clarify_reasons, key=CLARIFY_CODE_ORDER.__getitem__),),
            blocking_fields,
            _questions(findings),
            None,
        )

    amount = _amount(intent)
    requires_manager = any(
        rule.require == FINANCE_V1_POLICY.required_approver_above_limit
        and rule.when.strip().lower() == "always"
        for rule in intent.approval_rules
    )
    if amount is not None and amount > FINANCE_V1_POLICY.max_autonomous_payment_usd:
        return _decision(
            intent,
            Decision.ESCALATE,
            (ReasonCode.PAYMENT_ABOVE_AUTONOMOUS_LIMIT,),
            (),
            (),
            FINANCE_V1_POLICY.required_approver_above_limit,
        )
    if requires_manager:
        return _decision(
            intent,
            Decision.ESCALATE,
            (ReasonCode.FINANCE_MANAGER_APPROVAL_REQUIRED,),
            (),
            (),
            FINANCE_V1_POLICY.required_approver_above_limit,
        )

    return _decision(
        intent,
        Decision.APPROVE,
        (ReasonCode.REQUEST_ADMISSIBLE,),
        (),
        (),
        None,
    )


def _decision(
    intent: IntentSpec,
    decision: Decision,
    reason_codes: tuple[ReasonCode, ...],
    blocking_fields: tuple[str, ...],
    questions: tuple[str, ...],
    required_approver: str | None,
) -> ControlDecision:
    return ControlDecision(
        decision=decision,
        reason_codes=tuple(code.value for code in reason_codes),
        blocking_fields=blocking_fields,
        questions=questions,
        required_approver=required_approver,
        policy_version=FINANCE_V1_POLICY.policy_version,
        intent_id=intent.intent_id,
        intent_version=intent.version,
    )


def _reject_reasons(
    findings: tuple[ValidationFinding, ...],
) -> set[ReasonCode]:
    reasons: set[ReasonCode] = set()
    has_unbounded_permission = any(
        finding.code is FindingCode.UNBOUNDED_PERMISSIONS
        for finding in findings
    )
    for finding in findings:
        if (
            finding.code is FindingCode.UNKNOWN_OR_DISALLOWED_TOOL
            and not has_unbounded_permission
        ):
            reasons.add(ReasonCode.UNKNOWN_OR_DISALLOWED_TOOL)
        elif (
            finding.code is FindingCode.CONTRADICTORY_REQUIREMENTS
            and finding.field == "requirements"
        ):
            reasons.add(ReasonCode.CONTRADICTORY_REQUIREMENTS)
        elif (
            finding.code is FindingCode.UNBOUNDED_PERMISSIONS
            and "*" in finding.evidence.get("allowed_tools", ())
        ):
            reasons.add(ReasonCode.UNBOUNDED_PERMISSIONS)
        elif finding.code is FindingCode.UNSAFE_ASSUMPTION:
            reasons.add(ReasonCode.UNSAFE_ASSUMPTION)
        elif finding.code is FindingCode.NON_REVERSIBLE_HIGH_IMPACT_ACTION:
            reasons.add(ReasonCode.NON_REVERSIBLE_HIGH_IMPACT_ACTION)
        elif finding.code is FindingCode.POLICY_CONFLICT:
            reasons.add(_policy_reason(finding))
    return reasons


def _policy_reason(finding: ValidationFinding) -> ReasonCode:
    policy_rule = finding.evidence.get("policy_rule")
    return {
        "P1": ReasonCode.VENDOR_NOT_FOUND,
        "P2": ReasonCode.VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED,
        "P3": ReasonCode.PURCHASE_ORDER_INVALID,
        "P4": ReasonCode.DUPLICATE_INVOICE,
        "P7": ReasonCode.APPROVAL_BYPASS_PROHIBITED,
        "P8": ReasonCode.REQUIRED_VALIDATIONS_NOT_PASSED,
        "ACTOR_AUTHORITY": ReasonCode.ACTOR_UNAUTHORIZED,
        "FROZEN_WORKFLOW": ReasonCode.ACTION_OUTSIDE_FROZEN_WORKFLOW,
    }.get(policy_rule, ReasonCode.POLICY_CONFLICT)


def _clarify_reasons(
    findings: tuple[ValidationFinding, ...],
) -> set[ReasonCode]:
    mapping = {
        FindingCode.REQUIRED_FIELD_MISSING: ReasonCode.REQUIRED_FIELD_MISSING,
        FindingCode.AMBIGUOUS_ENTITY_REFERENCE: ReasonCode.AMBIGUOUS_ENTITY_REFERENCE,
        FindingCode.APPROVAL_RULE_MISSING: ReasonCode.APPROVAL_RULE_MISSING,
        FindingCode.CONTRADICTORY_REQUIREMENTS: ReasonCode.CONTRADICTORY_REQUIREMENTS,
        FindingCode.UNBOUNDED_PERMISSIONS: ReasonCode.UNBOUNDED_PERMISSIONS,
        FindingCode.SUCCESS_CONDITION_MISSING: ReasonCode.SUCCESS_CONDITION_MISSING,
    }
    return {mapping[finding.code] for finding in findings if finding.code in mapping}


def _questions(findings: tuple[ValidationFinding, ...]) -> tuple[str, ...]:
    questions: list[str] = []
    for finding in findings:
        if finding.code is FindingCode.REQUIRED_FIELD_MISSING:
            questions.append(f"Provide {finding.field}.")
        elif finding.code is FindingCode.AMBIGUOUS_ENTITY_REFERENCE:
            questions.append(f"Select one canonical value for {finding.field}.")
        elif finding.code is FindingCode.APPROVAL_RULE_MISSING:
            questions.append("Provide the finance-manager approval rule.")
        elif finding.code is FindingCode.CONTRADICTORY_REQUIREMENTS:
            questions.append(f"Resolve the conflict at {finding.field}.")
        elif finding.code is FindingCode.UNBOUNDED_PERMISSIONS:
            questions.append("Name the permitted frozen workflow tools.")
        elif finding.code is FindingCode.SUCCESS_CONDITION_MISSING:
            questions.append("Provide an observable success condition.")
    return tuple(dict.fromkeys(questions))


def _amount(intent: IntentSpec) -> Decimal | None:
    value = intent.inputs.get("amount")
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None
