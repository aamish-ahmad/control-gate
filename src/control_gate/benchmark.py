"""Deterministic fixture benchmark support for Control Gate V1."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from control_gate.compiler import FixtureCompiler, RequestFixture
from control_gate.contracts import Decision, IntentSpec
from control_gate.fixtures import FROZEN_DATASET_CATEGORIES, build_frozen_request_benchmark
from control_gate.validation import FindingCode, ValidationFinding, validate_intent


DEFAULT_FIXTURE_PATH = Path("benchmarks/requests.jsonl")
DEFAULT_PHASE_2_OUTPUT_DIR = Path("outputs/phase_2")
DEFAULT_PHASE_2_REPORT_PATH = Path("reports/phase_2_report.md")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )


def write_frozen_fixtures(path: Path = DEFAULT_FIXTURE_PATH) -> str:
    """Persist the reviewed in-memory catalog and return its content digest."""

    fixtures = build_frozen_request_benchmark()
    _write_jsonl(path, [fixture.model_dump(mode="json") for fixture in fixtures])
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixtures(path: Path = DEFAULT_FIXTURE_PATH) -> tuple[RequestFixture, ...]:
    """Load and validate nonblank fixture records without relabeling them."""

    fixtures: list[RequestFixture] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            fixtures.append(RequestFixture.model_validate_json(line))
        except Exception as error:
            raise ValueError(f"invalid fixture at {path}:{line_number}: {error}") from error
    return tuple(fixtures)


def _unique_codes(findings: tuple[ValidationFinding, ...]) -> tuple[FindingCode, ...]:
    return tuple(dict.fromkeys(finding.code for finding in findings))


def _fixture_result(fixture: RequestFixture, compiler: FixtureCompiler) -> dict[str, Any]:
    intent = compiler.compile(fixture)
    findings = validate_intent(intent)
    actual_codes = _unique_codes(findings)
    second_intent = compiler.compile(fixture)
    second_findings = validate_intent(second_intent)
    deterministic = (
        intent.model_dump_json() == second_intent.model_dump_json()
        and [finding.model_dump_json() for finding in findings]
        == [finding.model_dump_json() for finding in second_findings]
    )
    schema_valid = IntentSpec.model_validate_json(intent.model_dump_json()) == intent
    expected_codes = fixture.expected_finding_codes
    return {
        "fixture_id": fixture.fixture_id,
        "expected_decision": fixture.expected_decision.value,
        "expected_finding_codes": [code.value for code in expected_codes],
        "actual_finding_codes": [code.value for code in actual_codes],
        "finding_match": actual_codes == expected_codes,
        "compilation_success": True,
        "schema_valid": schema_valid,
        "deterministic": deterministic,
        "external_actions_performed": 0,
        "intent": intent.model_dump(mode="json"),
        "findings": [finding.model_dump(mode="json") for finding in findings],
    }


def _integrity(fixtures: tuple[RequestFixture, ...]) -> dict[str, bool]:
    distribution = Counter(fixture.expected_decision.value for fixture in fixtures)
    fixture_ids = [fixture.fixture_id for fixture in fixtures]
    requests = [fixture.request for fixture in fixtures]
    categories = {category for fixture in fixtures for category in fixture.categories}
    return {
        "total_is_48": len(fixtures) == 48,
        "balanced_decisions": distribution
        == Counter({decision.value: 12 for decision in Decision}),
        "fixture_ids_unique": len(fixture_ids) == len(set(fixture_ids)),
        "requests_unique": len(requests) == len(set(requests)),
        "required_categories_covered": FROZEN_DATASET_CATEGORIES <= categories,
        "schema_version_is_v1": all(
            fixture.fixture_schema_version == "control-gate.request-fixture.v1"
            for fixture in fixtures
        ),
    }


def run_phase_2_benchmark(
    fixture_path: Path = DEFAULT_FIXTURE_PATH,
    output_dir: Path = DEFAULT_PHASE_2_OUTPUT_DIR,
    report_path: Path = DEFAULT_PHASE_2_REPORT_PATH,
) -> dict[str, Any]:
    """Run fixture compilation and static validation, writing reproducible evidence."""

    fixtures = load_fixtures(fixture_path)
    compiler = FixtureCompiler()
    results = [_fixture_result(fixture, compiler) for fixture in fixtures]
    failures = [
        result
        for result in results
        if not (
            result["compilation_success"]
            and result["schema_valid"]
            and result["deterministic"]
            and result["finding_match"]
        )
    ]
    distribution = Counter(result["expected_decision"] for result in results)
    expected_codes = Counter(
        code
        for result in results
        for code in result["expected_finding_codes"]
    )
    actual_codes = Counter(
        code
        for result in results
        for code in result["actual_finding_codes"]
    )
    false_positives = sum(
        len(set(result["actual_finding_codes"]) - set(result["expected_finding_codes"]))
        for result in results
    )
    false_negatives = sum(
        len(set(result["expected_finding_codes"]) - set(result["actual_finding_codes"]))
        for result in results
    )
    integrity = _integrity(fixtures)
    summary: dict[str, Any] = {
        "phase": 2,
        "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "total_fixtures": len(fixtures),
        "decision_distribution": dict(sorted(distribution.items())),
        "compilation_success": sum(result["compilation_success"] for result in results),
        "schema_valid_count": sum(result["schema_valid"] for result in results),
        "exact_finding_agreement": sum(result["finding_match"] for result in results),
        "deterministic_repeatability": sum(result["deterministic"] for result in results),
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "expected_finding_counts": dict(sorted(expected_codes.items())),
        "actual_finding_counts": dict(sorted(actual_codes.items())),
        "benchmark_integrity": integrity,
        "external_actions_performed": 0,
        "phase_2_passed": (
            all(integrity.values())
            and not failures
            and false_positives == 0
            and false_negatives == 0
        ),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "fixture_results.jsonl", results)
    _write_jsonl(output_dir / "failures.jsonl", failures)
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(_phase_2_report(summary), encoding="utf-8", newline="\n")
    return summary


def _phase_2_report(summary: dict[str, Any]) -> str:
    integrity = "\n".join(
        f"| {name} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in summary["benchmark_integrity"].items()
    )
    return f"""# Phase 2 compiler and validator report

Result: {'PASS' if summary['phase_2_passed'] else 'FAIL'}

- Fixtures: {summary['total_fixtures']}
- Decision distribution: {json.dumps(summary['decision_distribution'], sort_keys=True)}
- Compilation success: {summary['compilation_success']}
- Schema-valid intents: {summary['schema_valid_count']}
- Exact static-finding agreement: {summary['exact_finding_agreement']}
- Deterministic repeats: {summary['deterministic_repeatability']}
- False positives: {summary['false_positives']}
- False negatives: {summary['false_negatives']}
- External actions: {summary['external_actions_performed']}
- Fixture SHA-256: {summary['fixture_sha256']}

| Integrity check | Result |
|---|---|
{integrity}

The fixture corpus was locally instantiated because no serialized corpus was
present in the repository or its history. The labels and expected findings are
loaded and evaluated without automatic relabeling.
"""


def phase_2_summary_json() -> str:
    """Run the default persisted benchmark and return structured JSON."""

    return json.dumps(run_phase_2_benchmark(), sort_keys=True)
