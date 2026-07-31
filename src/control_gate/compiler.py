"""Offline deterministic compiler for the frozen supplier-invoice fixture domain."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import ConfigDict, Field, JsonValue

from control_gate.contracts import (
    ApprovalRule,
    Decision,
    FrozenModel,
    Goal,
    IntentActor,
    IntentSpec,
    NonEmptyString,
    Permissions,
    PositiveVersion,
)
from control_gate.validation import FindingCode


INTENT_SCHEMA_VERSION = "control-gate.intent.v1"
FROZEN_PROHIBITED_ACTIONS = (
    "vendor.modify_bank_details",
    "payment.bypass_approval",
)
DEFAULT_REQUIREMENTS = (
    "verify_vendor",
    "validate_purchase_order",
    "detect_duplicate_invoice",
    "verify_amount",
)


class FixtureContext(FrozenModel):
    """Structured request context consumed by the deterministic compiler."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    intent_id: NonEmptyString | None = None
    action: NonEmptyString | None = None
    invoice_id: NonEmptyString | None = None
    supplier_id: NonEmptyString | None = None
    purchase_order_id: NonEmptyString | None = None
    amount: NonEmptyString | None = None
    currency: NonEmptyString | None = None
    constraint_currency: NonEmptyString | None = None
    actor_id: NonEmptyString | None = None
    actor_role: NonEmptyString | None = None
    requested_tools: tuple[NonEmptyString, ...] = ()
    requirements: tuple[NonEmptyString, ...] = DEFAULT_REQUIREMENTS
    assumptions: tuple[NonEmptyString, ...] = ()
    approval_rules: tuple[ApprovalRule, ...] = ()
    success_conditions: tuple[NonEmptyString, ...] = (
        "invoice_validated",
        "payment_authorized",
        "audit_event_written",
    )
    failure_conditions: tuple[NonEmptyString, ...] = (
        "vendor_missing",
        "duplicate_invoice",
        "purchase_order_mismatch",
        "approval_denied",
    )
    rollback_strategy: tuple[NonEmptyString, ...] = ("cancel_unsubmitted_payment",)
    entity_candidates: dict[str, tuple[NonEmptyString, ...]] = Field(
        default_factory=dict
    )
    supplier_exists: bool | None = None
    purchase_order_valid: bool | None = None
    duplicate_invoice: bool | None = None
    payment_validations_complete: bool | None = None
    permission_scope: Literal["bounded", "unbounded"] = "bounded"
    reversible: bool = True
    policy_bypass_requested: bool = False


class RequestFixture(FrozenModel):
    """Serialized benchmark case matching the frozen logical dataset schema."""

    fixture_id: NonEmptyString
    request: NonEmptyString
    context: FixtureContext
    expected_decision: Decision
    expected_reason_codes: tuple[NonEmptyString, ...]
    expected_finding_codes: tuple[FindingCode, ...] = ()
    required_intent_fields: tuple[NonEmptyString, ...]
    critical_policy: bool
    categories: tuple[NonEmptyString, ...]
    intent_version: PositiveVersion = 1
    fixture_schema_version: Literal["control-gate.request-fixture.v1"] = (
        "control-gate.request-fixture.v1"
    )


class FixtureCompiler:
    """Reference compiler used by tests and the committed V1 benchmark."""

    schema_version = INTENT_SCHEMA_VERSION

    def compile(self, fixture: RequestFixture) -> IntentSpec:
        """Compile one request without network, model, tool, or business actions."""

        context = fixture.context
        amount = _decimal_or_none(context.amount)
        if (
            context.action in {"submit_payment", "vendor.modify_bank_details"}
            or amount is not None
            and amount > Decimal("10000")
        ):
            risk_level = "high"
        elif context.amount is None:
            risk_level = "unresolved"
        else:
            risk_level = "medium"

        inputs: dict[str, JsonValue] = {
            "invoice_id": context.invoice_id,
            "supplier_id": context.supplier_id,
            "purchase_order_id": context.purchase_order_id,
            "amount": context.amount,
            "currency": context.currency,
            "entity_candidates": {
                key: list(values)
                for key, values in sorted(context.entity_candidates.items())
            },
            "supplier_exists": context.supplier_exists,
            "purchase_order_valid": context.purchase_order_valid,
            "duplicate_invoice": context.duplicate_invoice,
            "payment_validations_complete": context.payment_validations_complete,
            "policy_bypass_requested": context.policy_bypass_requested,
        }
        constraints: dict[str, JsonValue] = {
            "max_autonomous_payment_usd": "10000",
            "currency": context.constraint_currency or context.currency,
            "permission_scope": context.permission_scope,
            "reversible": context.reversible,
            "schema_version": self.schema_version,
        }

        return IntentSpec(
            intent_id=context.intent_id or f"INT-{fixture.fixture_id.upper()}",
            version=fixture.intent_version,
            source_request=fixture.request,
            goal=Goal(type=context.action or "unresolved"),
            actor=IntentActor(
                id=context.actor_id or "unresolved",
                role=context.actor_role or "unresolved",
            ),
            inputs=inputs,
            assumptions=context.assumptions,
            requirements=context.requirements,
            constraints=constraints,
            permissions=Permissions(allowed_tools=context.requested_tools),
            prohibited_actions=FROZEN_PROHIBITED_ACTIONS,
            approval_rules=context.approval_rules,
            risk_level=risk_level,
            success_conditions=context.success_conditions,
            failure_conditions=context.failure_conditions,
            rollback_strategy=context.rollback_strategy,
        )


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None
