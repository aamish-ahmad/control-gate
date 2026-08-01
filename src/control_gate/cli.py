"""Local, side-effect-free command-line interface for Control Gate V1."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any

from control_gate.admissibility_benchmark import run_phase_3_benchmark
from control_gate.evaluation import evaluate_request


def main(argv: Sequence[str] | None = None) -> int:
    """Run the local evaluation or the frozen benchmark."""

    parser = argparse.ArgumentParser(prog="control_gate")
    commands = parser.add_subparsers(dest="command", required=True)
    evaluate = commands.add_parser("evaluate", help="evaluate one supplier-invoice request")
    evaluate.add_argument("--request", required=True, help="business request to evaluate")
    commands.add_parser("benchmark", help="run the frozen 48-case benchmark")
    args = parser.parse_args(argv)

    if args.command == "evaluate":
        return _evaluate(args.request)
    return _benchmark()


def _evaluate(request: str) -> int:
    try:
        result = evaluate_request(request)
    except ValueError as error:
        _write_json(sys.stderr, {"error": {"code": "INVALID_REQUEST", "message": str(error)}})
        return 2
    _write_json(sys.stdout, result)
    return 0


def _benchmark() -> int:
    summary = run_phase_3_benchmark()
    status = "PASS" if summary["phase_3_passed"] else "FAIL"
    print(f"Control Gate benchmark: {status}")
    print(
        "Fixtures: {total}; decision matches: {decisions}; reason-code matches: {reasons}; "
        "deterministic repeats: {repeats}; macro-F1: {f1:.3f}; unsafe approvals: {unsafe}; "
        "external actions: {actions}".format(
            total=summary["total_fixtures"],
            decisions=summary["decision_matches"],
            reasons=summary["reason_matches"],
            repeats=summary["deterministic_repeatability"],
            f1=summary["decision_macro_f1"],
            unsafe=summary["unsafe_approval_count"],
            actions=summary["external_actions_performed"],
        )
    )
    return 0 if summary["phase_3_passed"] else 1


def _write_json(stream: Any, value: dict[str, Any]) -> None:
    stream.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
