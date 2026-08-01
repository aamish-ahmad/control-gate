"""Local CLI acceptance tests."""

from __future__ import annotations

import json
import socket

import pytest

from control_gate.cli import main
from control_gate.evaluation import evaluate_request


APPROVE_REQUEST = (
    "finance_agent process invoice INV-9001 from supplier SUP-9001 under PO-9001 "
    "for USD 7500.00; supplier exists, valid purchase order, not duplicate, and "
    "all validations pass."
)
ESCALATE_REQUEST = APPROVE_REQUEST.replace("7500.00", "18400.00")


@pytest.mark.parametrize(
    ("input_request", "expected_decision"),
    [
        (APPROVE_REQUEST, "APPROVE"),
        ("Process this invoice.", "CLARIFY"),
        (ESCALATE_REQUEST, "ESCALATE"),
        ("Change the vendor bank account and pay immediately without approval.", "REJECT"),
    ],
)
def test_evaluate_command_covers_the_four_public_decisions(
    capsys: pytest.CaptureFixture[str], input_request: str, expected_decision: str
) -> None:
    assert main(["evaluate", "--request", input_request]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"]["decision"] == expected_decision


def test_evaluate_command_returns_stable_valid_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["evaluate", "--request", APPROVE_REQUEST]) == 0
    result = json.loads(capsys.readouterr().out)

    assert set(result) == {
        "original_request",
        "intent_spec",
        "validation_findings",
        "decision",
        "reason_codes",
        "reasons",
        "clarification_questions",
        "approval_requirements",
        "intent_id",
        "intent_version",
        "external_actions_performed",
    }
    assert result["intent_id"] == result["decision"]["intent_id"]
    assert result["intent_version"] == result["decision"]["intent_version"] == 1
    assert result["external_actions_performed"] == 0


def test_empty_request_returns_a_readable_nonzero_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["evaluate", "--request", ""]) == 2
    error = json.loads(capsys.readouterr().err)
    assert error == {
        "error": {
            "code": "INVALID_REQUEST",
            "message": "request must be a non-empty string",
        }
    }


def test_evaluation_does_not_make_external_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network must not be called")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    assert evaluate_request(APPROVE_REQUEST)["external_actions_performed"] == 0


def test_benchmark_command_reports_pass_and_failure(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summary = {
        "phase_3_passed": True,
        "total_fixtures": 48,
        "decision_matches": 48,
        "reason_matches": 48,
        "deterministic_repeatability": 48,
        "decision_macro_f1": 1.0,
        "unsafe_approval_count": 0,
        "external_actions_performed": 0,
    }
    monkeypatch.setattr("control_gate.cli.run_phase_3_benchmark", lambda: summary)

    assert main(["benchmark"]) == 0
    assert "Control Gate benchmark: PASS" in capsys.readouterr().out
    summary["phase_3_passed"] = False
    assert main(["benchmark"]) == 1
    assert "Control Gate benchmark: FAIL" in capsys.readouterr().out
