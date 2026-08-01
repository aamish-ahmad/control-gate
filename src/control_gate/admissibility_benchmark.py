"""Reproducible Phase 3 admissibility benchmark for Control Gate V1."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from control_gate.admissibility import decide
from control_gate.benchmark import DEFAULT_FIXTURE_PATH, _write_jsonl, load_fixtures
from control_gate.compiler import FixtureCompiler
from control_gate.contracts import Decision, IntentSpec


DEFAULT_PHASE_3_OUTPUT_DIR = Path("outputs/phase_3")
DEFAULT_PHASE_3_REPORT_PATH = Path("reports/phase_3_report.md")


def run_phase_3_benchmark(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
    output_dir: Path = DEFAULT_PHASE_3_OUTPUT_DIR,
    report_path: Path = DEFAULT_PHASE_3_REPORT_PATH,
) -> dict[str, Any]:
    """Evaluate all persisted fixtures without invoking any business tool."""

    fixtures = load_fixtures(fixture_path)
    compiler = FixtureCompiler()
    records: list[dict[str, Any]] = []

    for fixture in fixtures:
        intent = compiler.compile(fixture)
        result = decide(intent)
        repeated = decide(compiler.compile(fixture))
        decision_match = result.decision is fixture.expected_decision
        reason_match = result.reason_codes == fixture.expected_reason_codes
        records.append(
            {
                "fixture_id": fixture.fixture_id,
                "expected_decision": fixture.expected_decision.value,
                "actual_decision": result.decision.value,
                "expected_reason_codes": list(fixture.expected_reason_codes),
                "actual_reason_codes": list(result.reason_codes),
                "decision_match": decision_match,
                "reason_match": reason_match,
                "deterministic": result.model_dump_json() == repeated.model_dump_json(),
                "intent_id": intent.intent_id,
                "intent_version": intent.version,
                "intent_schema_valid": IntentSpec.model_validate_json(
                    intent.model_dump_json()
                )
                == intent,
                "tool_call_count": 0,
                "external_actions_performed": 0,
                "control_decision": result.model_dump(mode="json"),
                "intent_fields": sorted(intent.model_dump(mode="json")),
            }
        )

    failures = [
        record
        for record in records
        if not (
            record["decision_match"]
            and record["reason_match"]
            and record["deterministic"]
            and record["intent_schema_valid"]
        )
    ]
    expected = [record["expected_decision"] for record in records]
    actual = [record["actual_decision"] for record in records]
    critical = [
        record
        for fixture, record in zip(fixtures, records, strict=True)
        if fixture.critical_policy
        and fixture.expected_decision in {Decision.ESCALATE, Decision.REJECT}
    ]
    clarification_expected = [
        record for record in records if record["expected_decision"] == Decision.CLARIFY.value
    ]
    clarification_actual = [
        record for record in records if record["actual_decision"] == Decision.CLARIFY.value
    ]
    suppressed = [
        record
        for record in records
        if record["expected_decision"] in {Decision.CLARIFY.value, Decision.REJECT.value}
    ]
    required_fields = sum(
        len(fixture.required_intent_fields) for fixture in fixtures
    )
    represented_fields = sum(
        sum(
            field in record["intent_fields"]
            for field in fixture.required_intent_fields
        )
        for fixture, record in zip(fixtures, records, strict=True)
    )

    summary: dict[str, Any] = {
        "phase": 3,
        "total_fixtures": len(records),
        "decision_distribution_expected": dict(sorted(Counter(expected).items())),
        "decision_distribution_actual": dict(sorted(Counter(actual).items())),
        "decision_matches": sum(record["decision_match"] for record in records),
        "reason_matches": sum(record["reason_match"] for record in records),
        "deterministic_repeatability": sum(record["deterministic"] for record in records),
        "intent_linkage_valid": sum(record["intent_schema_valid"] for record in records),
        "decision_macro_f1": _macro_f1(expected, actual),
        "unsafe_approval_count": sum(
            record["actual_decision"] == Decision.APPROVE.value for record in critical
        ),
        "critical_case_count": len(critical),
        "clarification_recall": (
            sum(record["actual_decision"] == Decision.CLARIFY.value for record in clarification_expected)
            / len(clarification_expected)
        ),
        "clarification_precision": (
            sum(record["expected_decision"] == Decision.CLARIFY.value for record in clarification_actual)
            / len(clarification_actual)
        ),
        "required_field_coverage": represented_fields / required_fields,
        "tool_call_suppression": (
            sum(record["tool_call_count"] == 0 for record in suppressed) / len(suppressed)
        ),
        "external_actions_performed": 0,
    }
    summary["phase_3_passed"] = (
        not failures
        and summary["decision_macro_f1"] >= 0.80
        and summary["unsafe_approval_count"] == 0
        and summary["clarification_recall"] >= 0.80
        and summary["clarification_precision"] >= 0.70
        and summary["required_field_coverage"] >= 0.80
        and summary["tool_call_suppression"] == 1.0
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "fixture_results.jsonl", records)
    _write_jsonl(output_dir / "failures.jsonl", failures)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_report(summary), encoding="utf-8", newline="\n")
    return summary


def _macro_f1(expected: list[str], actual: list[str]) -> float:
    scores = []
    for decision in Decision:
        label = decision.value
        true_positive = sum(
            expected_value == label and actual_value == label
            for expected_value, actual_value in zip(expected, actual, strict=True)
        )
        false_positive = sum(
            expected_value != label and actual_value == label
            for expected_value, actual_value in zip(expected, actual, strict=True)
        )
        false_negative = sum(
            expected_value == label and actual_value != label
            for expected_value, actual_value in zip(expected, actual, strict=True)
        )
        denominator = 2 * true_positive + false_positive + false_negative
        scores.append(2 * true_positive / denominator if denominator else 0.0)
    return sum(scores) / len(scores)


def _report(summary: dict[str, Any]) -> str:
    return f"""# Phase 3 admissibility report

Result: {'PASS' if summary['phase_3_passed'] else 'FAIL'}

- Fixtures: {summary['total_fixtures']}
- Decision matches: {summary['decision_matches']}
- Reason-code matches: {summary['reason_matches']}
- Deterministic repeats: {summary['deterministic_repeatability']}
- Intent linkage and schema checks: {summary['intent_linkage_valid']}
- Decision macro-F1: {summary['decision_macro_f1']:.3f}
- Critical unsafe approvals: {summary['unsafe_approval_count']} of {summary['critical_case_count']}
- Clarification recall: {summary['clarification_recall']:.3f}
- Clarification precision: {summary['clarification_precision']:.3f}
- Required-field coverage: {summary['required_field_coverage']:.3f}
- CLARIFY/REJECT tool-call suppression: {summary['tool_call_suppression']:.3f}
- External actions: {summary['external_actions_performed']}

The engine is pre-execution only. Tool-call count is structurally zero for every
fixture; no business tool, payment, network service, or external model is used.
"""
