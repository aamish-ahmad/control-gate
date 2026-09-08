"""Reproduce bounded C4 acceptance traces; not a benchmark or experiment."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
import json

from control_gate import invoice_runtime as runtime
from control_gate.contracts import HumanIntervention, IntentSpec, RunState
from control_gate.evaluation import compile_request
from control_gate.human_control import intent_digest, scope
from control_gate.tool_environment import build_local_tool_environment


class Spy:
    def __init__(self):
        self.environment = build_local_tool_environment()
        self.calls = []

    def __getattr__(self, tool):
        def invoke(**arguments):
            self.calls.append({"tool": tool, "arguments": {
                key: value.model_dump(mode="json") if isinstance(value, HumanIntervention) else value
                for key, value in arguments.items()}})
            return getattr(self.environment, tool)(**arguments)
        return invoke


def human(run, action, changes):
    return HumanIntervention(
        intervention_id=f"H-{uuid4()}", run_id=run.run_id, intent_id=run.intent_id,
        intent_version=run.intent_version, timestamp=datetime.now(timezone.utc),
        actor_id="local-human-manager", actor_role="finance_manager", action=action,
        reason="Explicit review of this bounded local invoice action",
        constraint_changes={"intent_digest": intent_digest(run.intent_spec), **changes})


def main():
    cases = []
    high = runtime.DEMO_REQUEST.replace("1001", "2001").replace("7500.00", "18400.00")
    for name in ("clarify_inputs", "approve_escalation", "deny", "cancel", "narrow_cap", "narrow_permissions"):
        spy = Spy()
        if name in ("clarify_inputs", "narrow_cap", "narrow_permissions"):
            data = compile_request(runtime.DEMO_REQUEST).model_dump(mode="json")
            data["inputs"].pop("amount")
            parent = runtime.execute_invoice(IntentSpec.model_validate(data), spy)
            changes = {"inputs": {"amount": "7500"}}
            if name == "narrow_cap":
                changes["constraints"] = {"max_autonomous_payment_usd": 5000}
            if name == "narrow_permissions":
                changes["allowed_tools"] = ["invoice.parse", "vendor.lookup", "po.lookup"]
            intervention = human(parent, "MODIFY_CONSTRAINT", changes)
        else:
            parent = runtime.execute_invoice(high, spy)
            action = {"approve_escalation": "APPROVE", "deny": "DENY", "cancel": "CANCEL"}[name]
            intervention = human(parent, action, {"approved_action": scope(parent.intent_spec)} if action == "APPROVE" else {})
        assert not spy.calls
        before = parent.model_dump(mode="json")
        review = runtime.intervention_request(parent)
        child = runtime.resume_invoice(parent, intervention)
        expected = {"clarify_inputs": RunState.COMPLETED, "approve_escalation": RunState.COMPLETED,
                    "deny": RunState.REJECTED, "cancel": RunState.CANCELLED,
                    "narrow_cap": RunState.REJECTED, "narrow_permissions": RunState.REJECTED}[name]
        assert child.state is expected
        stages = len(spy.environment.staged_payments)
        assert stages == (1 if expected is RunState.COMPLETED else 0)
        if not stages:
            assert all(call["tool"] != "stage_payment" for call in spy.calls)
        calls_before_replay = len(spy.calls)
        try:
            runtime.resume_invoice(parent, intervention)
            raise AssertionError("Consumed intervention replayed")
        except ValueError:
            pass
        assert len(spy.calls) == calls_before_replay
        cases.append({"case": name, "review": review, "parent_before": before,
            "human_decision": intervention.model_dump(mode="json"),
            "parent_after": parent.model_dump(mode="json"),
            "continuation": child.model_dump(mode="json") if child is not parent else None,
            "observed_calls": spy.calls, "staged_payments": stages, "replay_new_calls": 0})
    for field, value in (("invoice_id", "INV-1001"), ("amount", "19000"), ("currency", "EUR")):
        spy = Spy()
        parent = runtime.execute_invoice(high, spy)
        before = parent.model_dump(mode="json")
        original = runtime._propose
        def attacked(run, tool):
            proposal = original(run, tool)
            if tool == "stage_payment":
                proposal["arguments"][field] = value
            return proposal
        runtime._propose = attacked
        intervention = human(parent, "APPROVE", {"approved_action": scope(parent.intent_spec)})
        try:
            child = runtime.resume_invoice(parent, intervention)
        finally:
            runtime._propose = original
        assert child.state is RunState.REJECTED and len(spy.calls) == 5
        assert not spy.environment.staged_payments
        cases.append({"case": f"approved_then_attacked_{field}", "parent_before": before,
            "human_decision": intervention.model_dump(mode="json"),
            "parent_after": parent.model_dump(mode="json"), "continuation": child.model_dump(mode="json"),
            "observed_calls": spy.calls, "staged_payments": 0})
    packet = {"phase": "C4", "evidence_type": "bounded acceptance trajectories",
              "external_actions_performed": 0, "cases": cases}
    path = Path(__file__).with_name("human_control_proof.json")
    path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"cases": len(cases), "completed": 2, "blocked_or_cancelled": 7,
                      "external_actions_performed": 0, "proof": str(path)}))


if __name__ == "__main__":
    main()
