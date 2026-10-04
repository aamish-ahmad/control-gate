"""Reproduce the bounded C5 failure/recovery matrix; not an experiment."""

from datetime import datetime, timezone
import json
from pathlib import Path

from control_gate import invoice_runtime as runtime
from control_gate.contracts import HumanAction, HumanIntervention, RunState
from control_gate.human_control import intent_digest
from control_gate.tool_environment import (
    FailureInjectingToolEnvironment, InjectedFailureMode, PurchaseOrderRecord,
    build_local_tool_environment,
)


def request(invoice="INV-1001", supplier="SUP-1001", po="PO-1001", amount="7500.00"):
    return (f"finance_agent process invoice {invoice} from supplier {supplier} under {po} "
            f"for USD {amount}; supplier exists, valid purchase order, not duplicate, "
            "and all validations pass.")


def injected(**failures):
    base = build_local_tool_environment()
    return base, FailureInjectingToolEnvironment(base, failures=failures)


def record(name, run, environment):
    decision = run.runtime_decision or run.gate_a
    return {"case": name, "state": run.state.value,
            "runtime_reason_codes": list(decision.reason_codes),
            "retry_events": sum(event.event_type.value == "retry_scheduled"
                                for event in run.events),
            "tool_attempts": len(run.tool_history),
            "staged_payments": len(environment.staged_payments),
            "external_actions_performed": 0,
            "run": run.model_dump(mode="json")}


class ContradictoryEnvironment:
    def __init__(self):
        self.base = build_local_tool_environment()

    @property
    def staged_payments(self):
        return self.base.staged_payments

    def __getattr__(self, name):
        return getattr(self.base, name)

    def lookup_purchase_order(self, purchase_order_id):
        po = self.base.lookup_purchase_order(purchase_order_id)
        return PurchaseOrderRecord.model_validate({
            **po.model_dump(mode="json"), "supplier_id": "SUP-2001"})


def main():
    cases = []

    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED and len(base.staged_payments) == 1
    cases.append(record("timeout_recovered", run, base))

    base, environment = injected(lookup_supplier=(
        InjectedFailureMode.MALFORMED_TOOL_RESPONSE,
        InjectedFailureMode.MALFORMED_TOOL_RESPONSE))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.COMPLETED and len(base.staged_payments) == 1
    cases.append(record("malformed_response_recovered_at_cap", run, base))

    base, environment = injected(retrieve_policy=(
        InjectedFailureMode.TOOL_TIMEOUT, InjectedFailureMode.TOOL_TIMEOUT,
        InjectedFailureMode.TOOL_TIMEOUT))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and len(base.staged_payments) == 0
    cases.append(record("repeated_failure_exhausted", run, base))

    base, environment = injected(stage_payment=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and len(base.staged_payments) == 0
    cases.append(record("staging_timeout_not_retried", run, base))

    base, environment = injected(lookup_supplier=(InjectedFailureMode.PERMISSION_DENIED,))
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.FAILED and len(base.staged_payments) == 0
    cases.append(record("permission_denied_terminal", run, base))

    environment = build_local_tool_environment()
    run = runtime.execute_invoice(request("INV-9999"), environment)
    assert run.state is RunState.FAILED and len(environment.staged_payments) == 0
    cases.append(record("missing_record_terminal", run, environment))

    environment = ContradictoryEnvironment()
    run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    assert run.state is RunState.REJECTED and len(environment.staged_payments) == 0
    cases.append(record("po_invoice_contradiction_blocked", run, environment))

    environment = build_local_tool_environment()
    run = runtime.execute_invoice(request("INV-3001"), environment)
    assert run.state is RunState.FAILED and len(environment.staged_payments) == 0
    cases.append(record("duplicate_invoice_terminal", run, environment))

    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    original = runtime._propose

    def changed(state, tool):
        proposal = original(state, tool)
        if state.retry_state.get("attempts"):
            proposal["arguments"]["invoice_id"] = "INV-3001"
        return proposal

    runtime._propose = changed
    try:
        run = runtime.execute_invoice(runtime.DEMO_REQUEST, environment)
    finally:
        runtime._propose = original
    assert run.state is RunState.REJECTED and len(base.staged_payments) == 0
    cases.append(record("retry_resource_change_blocked_by_gate_b", run, base))

    high = runtime.DEMO_REQUEST.replace("1001", "2001").replace("7500.00", "18400.00")
    base, environment = injected(inspect_invoice=(InjectedFailureMode.TOOL_TIMEOUT,))
    run = runtime.execute_invoice(high, environment)
    intervention = HumanIntervention(
        intervention_id="H-C5-PROOF-DENY", run_id=run.run_id, intent_id=run.intent_id,
        intent_version=run.intent_version, timestamp=datetime.now(timezone.utc),
        actor_id="local-human-manager", actor_role="finance_manager", action=HumanAction.DENY,
        reason="Deny this exact invoice action",
        constraint_changes={"intent_digest": intent_digest(run.intent_spec)})
    run = runtime.resume_invoice(run, intervention)
    assert run.state is RunState.REJECTED and len(base.staged_payments) == 0
    cases.append(record("human_denial_not_retried", run, base))

    packet = {"phase": "C5", "evidence_type": "bounded failure and recovery matrix",
              "external_actions_performed": 0, "cases": cases}
    path = Path(__file__).with_name("recovery_proof.json")
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"cases": len(cases), "recovered": 2, "safe_stops": 8,
                      "external_actions_performed": 0, "proof": str(path)}))


if __name__ == "__main__":
    main()
