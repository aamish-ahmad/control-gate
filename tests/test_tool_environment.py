"""C1 tests for the deterministic bounded local tool environment."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from control_gate.contracts import FINANCE_V1_POLICY
from control_gate.tool_environment import (
    LocalToolError,
    LocalToolErrorCode,
    PurchaseOrderStatus,
    build_local_tool_environment,
)


def test_fixture_environment_is_deterministic_isolated_and_immutable() -> None:
    first = build_local_tool_environment()
    second = build_local_tool_environment()

    assert first.lookup_supplier("SUP-1001") == second.lookup_supplier("SUP-1001")
    assert first.lookup_purchase_order("PO-1001").status is PurchaseOrderStatus.OPEN
    assert first.inspect_invoice("INV-1001") == second.inspect_invoice("INV-1001")
    assert first.staged_payments == second.staged_payments == ()
    with pytest.raises(ValidationError, match="frozen"):
        first.lookup_supplier("SUP-1001").active = False


@pytest.mark.parametrize(
    ("operation", "identifier"),
    [
        ("lookup_supplier", "SUP-UNKNOWN"),
        ("lookup_purchase_order", "PO-UNKNOWN"),
        ("inspect_invoice", "INV-UNKNOWN"),
        ("retrieve_policy", "finance-unknown"),
    ],
)
def test_read_tools_fail_closed_for_unknown_records(
    operation: str, identifier: str
) -> None:
    environment = build_local_tool_environment()

    with pytest.raises(LocalToolError) as raised:
        getattr(environment, operation)(identifier)

    assert raised.value.tool == operation
    assert raised.value.code is LocalToolErrorCode.RECORD_NOT_FOUND


def test_duplicate_check_and_policy_retrieval_are_stable() -> None:
    environment = build_local_tool_environment()

    clear = environment.check_duplicate("INV-1001")
    duplicate = environment.check_duplicate("INV-3001")

    assert clear.is_duplicate is False
    assert clear.matching_invoice_id is None
    assert duplicate.is_duplicate is True
    assert duplicate.matching_invoice_id == "INV-1001"
    assert environment.retrieve_policy() == FINANCE_V1_POLICY


def test_stage_payment_is_local_idempotent_and_fully_linked() -> None:
    environment = build_local_tool_environment()

    first = environment.stage_payment(
        invoice_id="INV-1001",
        purchase_order_id="PO-1001",
        amount="7500.00",
        currency="usd",
    )
    second = environment.stage_payment(
        invoice_id="INV-1001",
        purchase_order_id="PO-1001",
        amount=Decimal("7500.00"),
        currency="USD",
    )

    assert first is second
    assert first.stage_id == "STAGE-INV-1001"
    assert first.invoice_id == "INV-1001"
    assert first.purchase_order_id == "PO-1001"
    assert first.supplier_id == "SUP-1001"
    assert first.currency == "USD"
    assert first.status == "STAGED_FOR_LOCAL_SIMULATION"
    assert first.external_actions_performed == 0
    assert environment.staged_payments == (first,)


@pytest.mark.parametrize(
    ("invoice_id", "purchase_order_id", "amount", "currency", "expected_code"),
    [
        ("INV-3001", "PO-1001", "7500.00", "USD", LocalToolErrorCode.DUPLICATE_INVOICE),
        ("INV-3002", "PO-3001", "2500.00", "USD", LocalToolErrorCode.INACTIVE_SUPPLIER),
        ("INV-4001", "PO-4001", "4200.00", "USD", LocalToolErrorCode.AMOUNT_MISMATCH),
        ("INV-1001", "PO-2001", "7500.00", "USD", LocalToolErrorCode.INVOICE_PURCHASE_ORDER_MISMATCH),
        ("INV-1001", "PO-1001", "7500.00", "EUR", LocalToolErrorCode.CURRENCY_MISMATCH),
        ("INV-2001", "PO-2001", "18400.00", "USD", LocalToolErrorCode.APPROVAL_REQUIRED),
    ],
)
def test_stage_payment_blocks_unsafe_or_inconsistent_actions(
    invoice_id: str,
    purchase_order_id: str,
    amount: str,
    currency: str,
    expected_code: LocalToolErrorCode,
) -> None:
    environment = build_local_tool_environment()

    with pytest.raises(LocalToolError) as raised:
        environment.stage_payment(
            invoice_id=invoice_id,
            purchase_order_id=purchase_order_id,
            amount=amount,
            currency=currency,
        )

    assert raised.value.tool == "stage_payment"
    assert raised.value.code is expected_code
    assert environment.staged_payments == ()


@pytest.mark.parametrize("amount", ("", "NaN", "Infinity", "-1", 0))
def test_staging_rejects_invalid_amounts(amount: str | int) -> None:
    environment = build_local_tool_environment()

    with pytest.raises(LocalToolError) as raised:
        environment.stage_payment(
            invoice_id="INV-1001",
            purchase_order_id="PO-1001",
            amount=amount,
            currency="USD",
        )

    assert raised.value.code is LocalToolErrorCode.INVALID_ARGUMENT


def test_request_human_approval_creates_only_a_local_pending_record() -> None:
    environment = build_local_tool_environment()

    first = environment.request_human_approval(
        invoice_id="INV-2001",
        purchase_order_id="PO-2001",
        amount="18400.00",
        currency="USD",
        requested_by="finance_agent",
        reason="Amount exceeds the autonomous policy threshold.",
    )
    second = environment.request_human_approval(
        invoice_id="INV-2001",
        purchase_order_id="PO-2001",
        amount="18400.00",
        currency="USD",
        requested_by="finance_agent",
        reason="Amount exceeds the autonomous policy threshold.",
    )

    assert first is second
    assert first.approval_request_id == "APPROVAL-INV-2001"
    assert first.required_approver == "finance_manager"
    assert first.status == "PENDING_LOCAL_APPROVAL"
    assert first.external_actions_performed == 0
    assert environment.approval_requests == (first,)
    assert environment.staged_payments == ()


def test_request_human_approval_requires_a_reason_and_requester() -> None:
    environment = build_local_tool_environment()

    with pytest.raises(LocalToolError) as raised:
        environment.request_human_approval(
            invoice_id="INV-2001",
            purchase_order_id="PO-2001",
            amount="18400.00",
            currency="USD",
            requested_by=" ",
            reason=" ",
        )

    assert raised.value.tool == "request_human_approval"
    assert raised.value.code is LocalToolErrorCode.INVALID_ARGUMENT
    assert environment.approval_requests == ()
