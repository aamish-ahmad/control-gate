"""Deterministic request adapter and structured pre-execution evaluation."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from control_gate.admissibility import ReasonCode, decide
from control_gate.compiler import FixtureCompiler, FixtureContext, RequestFixture
from control_gate.contracts import ApprovalRule, Decision, IntentSpec
from control_gate.validation import validate_intent


_ID_PATTERNS = {
    "invoice_id": re.compile(r"\bINV-[A-Za-z0-9-]+\b", re.IGNORECASE),
    "supplier_id": re.compile(r"\b(?:SUP|VENDOR)-[A-Za-z0-9-]+\b", re.IGNORECASE),
    "purchase_order_id": re.compile(r"\bPO-[A-Za-z0-9-]+\b", re.IGNORECASE),
}
_AMOUNT_PATTERN = re.compile(
    r"\b(?P<currency>USD|EUR|GBP)\s*(?P<amount>\d+(?:\.\d{1,2})?)\b|\$(?P<dollar_amount>\d+(?:\.\d{1,2})?)",
    re.IGNORECASE,
)

_REASON_MESSAGES = {
    ReasonCode.REQUEST_ADMISSIBLE.value: "The request is complete, permitted, and within autonomous authority.",
    ReasonCode.PAYMENT_ABOVE_AUTONOMOUS_LIMIT.value: "The amount exceeds the USD 10,000 autonomous payment limit.",
    ReasonCode.FINANCE_MANAGER_APPROVAL_REQUIRED.value: "A finance-manager approval rule requires a human decision.",
    ReasonCode.REQUIRED_FIELD_MISSING.value: "Material supplier-invoice information is missing.",
    ReasonCode.AMBIGUOUS_ENTITY_REFERENCE.value: "A referenced business entity is ambiguous.",
    ReasonCode.APPROVAL_RULE_MISSING.value: "The request needs a finance-manager approval rule.",
    ReasonCode.CONTRADICTORY_REQUIREMENTS.value: "The request contains incompatible requirements.",
    ReasonCode.UNBOUNDED_PERMISSIONS.value: "The request asks for unbounded tool permissions.",
    ReasonCode.UNKNOWN_OR_DISALLOWED_TOOL.value: "The request names a tool outside the frozen workflow.",
    ReasonCode.UNSAFE_ASSUMPTION.value: "The request relies on an unsafe validation-bypassing assumption.",
    ReasonCode.SUCCESS_CONDITION_MISSING.value: "The request has no observable success condition.",
    ReasonCode.NON_REVERSIBLE_HIGH_IMPACT_ACTION.value: "The request proposes a non-reversible high-impact action.",
    ReasonCode.VENDOR_NOT_FOUND.value: "The supplier does not exist.",
    ReasonCode.VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED.value: "Supplier bank details may not be modified.",
    ReasonCode.PURCHASE_ORDER_INVALID.value: "The purchase order is not valid.",
    ReasonCode.DUPLICATE_INVOICE.value: "Duplicate invoices must be rejected.",
    ReasonCode.APPROVAL_BYPASS_PROHIBITED.value: "Approval may not be bypassed.",
    ReasonCode.REQUIRED_VALIDATIONS_NOT_PASSED.value: "All required payment validations must pass first.",
    ReasonCode.ACTOR_UNAUTHORIZED.value: "The stated actor is not authorized for this workflow.",
    ReasonCode.ACTION_OUTSIDE_FROZEN_WORKFLOW.value: "The requested action is outside the frozen supplier-invoice workflow.",
    ReasonCode.POLICY_CONFLICT.value: "The request conflicts with the frozen policy.",
}


def compile_request(request: str) -> IntentSpec:
    """Compile explicit request details into the existing deterministic contract."""

    normalized = _normalise_request(request)
    context = _context_from_request(normalized)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16].upper()
    fixture = RequestFixture(
        fixture_id=f"CLI-{digest}",
        request=normalized,
        context=context,
        expected_decision=Decision.CLARIFY,
        expected_reason_codes=("INTERACTIVE_REQUEST",),
        required_intent_fields=tuple(IntentSpec.model_fields),
        critical_policy=False,
        categories=("interactive_cli",),
    )
    return FixtureCompiler().compile(fixture)


def evaluate_request(request: str) -> dict[str, Any]:
    """Return a JSON-ready, side-effect-free Control Gate evaluation."""

    original_request = _normalise_request(request)
    intent = compile_request(original_request)
    findings = validate_intent(intent)
    control = decide(intent, findings)
    return {
        "original_request": original_request,
        "intent_spec": intent.model_dump(mode="json"),
        "validation_findings": [finding.model_dump(mode="json") for finding in findings],
        "decision": control.model_dump(mode="json"),
        "reason_codes": list(control.reason_codes),
        "reasons": [
            {"code": code, "message": _REASON_MESSAGES[code]}
            for code in control.reason_codes
        ],
        "clarification_questions": list(control.questions),
        "approval_requirements": (
            {"required_approver": control.required_approver}
            if control.required_approver is not None
            else None
        ),
        "intent_id": intent.intent_id,
        "intent_version": intent.version,
        "external_actions_performed": 0,
    }


def _normalise_request(request: str) -> str:
    if not isinstance(request, str) or not request.strip():
        raise ValueError("request must be a non-empty string")
    return request.strip()


def _context_from_request(request: str) -> FixtureContext:
    lower = request.lower()
    identifiers = {
        field: _first_identifier(pattern, request)
        for field, pattern in _ID_PATTERNS.items()
    }
    amount, currency = _amount_and_currency(request)
    bank_change = "bank account" in lower or "bank details" in lower
    invoice_action = any(token in lower for token in ("invoice", "process", "pay"))
    action = "vendor.modify_bank_details" if bank_change else (
        "process_supplier_invoice" if invoice_action else None
    )
    actor = "finance_agent" if "finance_agent" in lower else None
    actor_role = "automated_finance_operator" if actor else None
    is_complete = (
        identifiers["invoice_id"] is not None
        and identifiers["supplier_id"] is not None
        and identifiers["purchase_order_id"] is not None
        and amount is not None
        and currency is not None
    )
    validation_confirmed = any(
        phrase in lower
        for phrase in ("all validations pass", "all checks pass", "all frozen checks pass")
    )
    supplier_exists = True if "supplier exists" in lower or "vendor exists" in lower else None
    if "supplier does not exist" in lower or "vendor does not exist" in lower:
        supplier_exists = False
    po_valid = True if "valid purchase order" in lower or "po is valid" in lower else None
    if "invalid purchase order" in lower or "po is invalid" in lower:
        po_valid = False
    duplicate = True if "duplicate invoice" in lower and "not duplicate" not in lower else None
    if "not duplicate" in lower or "nonduplicate" in lower:
        duplicate = False
    bypass = "bypass approval" in lower or "without approval" in lower
    return FixtureContext(
        action=action,
        invoice_id=identifiers["invoice_id"],
        supplier_id=identifiers["supplier_id"],
        purchase_order_id=identifiers["purchase_order_id"],
        amount=amount,
        currency=currency,
        actor_id=actor,
        actor_role=actor_role,
        requested_tools=(
            ("invoice.parse", "vendor.lookup", "po.lookup", "payment.submit")
            if action == "process_supplier_invoice"
            else ()
        ),
        approval_rules=(ApprovalRule(when="amount > 10000", require="finance_manager"),),
        supplier_exists=supplier_exists if supplier_exists is not None else (True if is_complete else None),
        purchase_order_valid=po_valid if po_valid is not None else (True if is_complete else None),
        duplicate_invoice=duplicate if duplicate is not None else (False if is_complete else None),
        payment_validations_complete=(
            True if validation_confirmed else (True if is_complete else None)
        ),
        policy_bypass_requested=bypass,
    )


def _first_identifier(pattern: re.Pattern[str], request: str) -> str | None:
    match = pattern.search(request)
    return match.group(0).upper() if match else None


def _amount_and_currency(request: str) -> tuple[str | None, str | None]:
    match = _AMOUNT_PATTERN.search(request)
    if match is None:
        return None, None
    currency = match.group("currency")
    amount = match.group("amount") or match.group("dollar_amount")
    return amount, currency.upper() if currency else "USD"
