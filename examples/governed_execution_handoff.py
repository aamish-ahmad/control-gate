"""Local fictional handoff after a real Control Gate admissibility decision."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from typing import Any

from control_gate.admissibility import decide
from control_gate.contracts import Decision, IntentSpec
from control_gate.evaluation import compile_request
from control_gate.validation import validate_intent


APPROVE_REQUEST = (
    "finance_agent process invoice INV-9001 from supplier SUP-9001 under PO-9001 "
    "for USD 7500.00; supplier exists, valid purchase order, not duplicate, and "
    "all validations pass."
)

StageFunction = Callable[[IntentSpec], dict[str, Any]]


def stage_invoice_locally(intent_spec: IntentSpec) -> dict[str, Any]:
    """Return an in-memory staging record without performing an external action."""

    return {
        "operation": "stage_invoice_locally",
        "status": "STAGED_FOR_LOCAL_SIMULATION",
        "simulation": "LOCAL_FICTIONAL_SUPPLIER_INVOICE",
        "invoice_id": intent_spec.inputs.get("invoice_id"),
        "intent_id": intent_spec.intent_id,
        "intent_version": intent_spec.version,
        "external_actions_performed": 0,
    }


def governed_execution_handoff(
    request: str,
    stage_function: StageFunction = stage_invoice_locally,
) -> dict[str, Any]:
    """Evaluate one request and route only APPROVE to local mock staging."""

    intent_spec = compile_request(request)
    findings = validate_intent(intent_spec)
    control_decision = decide(intent_spec, findings)
    approved = control_decision.decision is Decision.APPROVE
    handoff = stage_function(intent_spec) if approved else None

    return {
        "original_request": intent_spec.source_request,
        "intent": {
            "intent_id": intent_spec.intent_id,
            "intent_version": intent_spec.version,
        },
        "decision": {
            "outcome": control_decision.decision.value,
            "reason_codes": list(control_decision.reason_codes),
            "clarification_questions": list(control_decision.questions),
            "approval_requirement": (
                {"required_approver": control_decision.required_approver}
                if control_decision.required_approver is not None
                else None
            ),
            "intent_id": control_decision.intent_id,
            "intent_version": control_decision.intent_version,
        },
        "routing": {
            "staging_invoked": approved,
            "handoff": handoff,
        },
        "simulation": "LOCAL_FICTIONAL_SUPPLIER_INVOICE",
        "external_actions_performed": 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run the local fictional governed-execution handoff."
    )
    parser.add_argument("--request", default=APPROVE_REQUEST)
    args = parser.parse_args(argv)
    print(json.dumps(governed_execution_handoff(args.request), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
