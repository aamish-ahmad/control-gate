"""Phase 2 compiler, validator, fixture, and benchmark acceptance tests."""

from __future__ import annotations

import socket
from pathlib import Path

import pytest
from pydantic import ValidationError

from control_gate.benchmark import (
    load_fixtures,
    run_phase_2_benchmark,
    write_frozen_fixtures,
)
from control_gate.compiler import FixtureCompiler, RequestFixture
from control_gate.contracts import IntentSpec
from control_gate.fixtures import build_frozen_request_benchmark
from control_gate.validation import FindingCode, validate_intent


def test_fixture_catalog_is_frozen_balanced_and_covers_validator_rules() -> None:
    fixtures = build_frozen_request_benchmark()

    assert len(fixtures) == 48
    assert {
        decision: sum(fixture.expected_decision.value == decision for fixture in fixtures)
        for decision in ("APPROVE", "CLARIFY", "ESCALATE", "REJECT")
    } == {
        "APPROVE": 12,
        "CLARIFY": 12,
        "ESCALATE": 12,
        "REJECT": 12,
    }
    expected_codes = {
        code
        for fixture in fixtures
        for code in fixture.expected_finding_codes
    }
    assert expected_codes == set(FindingCode) - {FindingCode.SCHEMA_INVALID}
    assert len({fixture.fixture_id for fixture in fixtures}) == 48
    assert len({fixture.request for fixture in fixtures}) == 48


def test_compiler_is_deterministic_and_preserves_intent_version_linkage() -> None:
    fixture = build_frozen_request_benchmark()[0]
    compiler = FixtureCompiler()

    first = compiler.compile(fixture)
    second = compiler.compile(fixture)
    next_version = fixture.model_copy(update={"intent_version": 2})
    revised = compiler.compile(next_version)

    assert first.model_dump_json() == second.model_dump_json()
    assert (revised.intent_id, revised.version) == (first.intent_id, 2)
    assert first.version == 1
    with pytest.raises(TypeError):
        first.inputs["invoice_id"] = "MUTATED"
    assert IntentSpec.model_validate_json(first.model_dump_json()) == first


def test_compiler_exposes_missing_values_without_guessing() -> None:
    fixture = next(
        item
        for item in build_frozen_request_benchmark()
        if item.fixture_id == "CG-CLR-01"
    )

    intent = FixtureCompiler().compile(fixture)

    assert intent.inputs["invoice_id"] is None
    assert intent.source_request == fixture.request
    assert FindingCode.REQUIRED_FIELD_MISSING in {
        finding.code for finding in validate_intent(intent)
    }


def test_validator_matches_every_persisted_fixture_expectation() -> None:
    compiler = FixtureCompiler()

    for fixture in build_frozen_request_benchmark():
        actual_codes = tuple(
            dict.fromkeys(
                finding.code for finding in validate_intent(compiler.compile(fixture))
            )
        )
        assert actual_codes == fixture.expected_finding_codes, fixture.fixture_id


def test_validator_reports_schema_invalid_for_malformed_candidate() -> None:
    intent = FixtureCompiler().compile(build_frozen_request_benchmark()[0])
    payload = intent.model_dump()
    payload["unfrozen_field"] = "not permitted"

    findings = validate_intent(payload)

    assert findings
    assert {finding.code for finding in findings} == {FindingCode.SCHEMA_INVALID}


def test_malformed_fixture_is_rejected() -> None:
    payload = build_frozen_request_benchmark()[0].model_dump()
    payload["unexpected"] = True

    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        RequestFixture.model_validate(payload)


def test_compiler_and_validator_make_no_network_action(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network must not be called")

    monkeypatch.setattr(socket, "create_connection", fail_network)
    fixture = build_frozen_request_benchmark()[0]
    intent = FixtureCompiler().compile(fixture)

    assert validate_intent(intent) == ()


def test_phase_2_benchmark_is_reproducible_and_persists_evidence(
    tmp_path: Path,
) -> None:
    fixture_path = tmp_path / "requests.jsonl"
    output_dir = tmp_path / "outputs"
    report_path = tmp_path / "phase_2_report.md"

    digest = write_frozen_fixtures(fixture_path)
    loaded = load_fixtures(fixture_path)
    first = run_phase_2_benchmark(fixture_path, output_dir, report_path)
    first_results = (output_dir / "fixture_results.jsonl").read_bytes()
    second = run_phase_2_benchmark(fixture_path, output_dir, report_path)

    assert len(loaded) == 48
    assert digest == first["fixture_sha256"]
    assert first == second
    assert first["phase_2_passed"] is True
    assert first["external_actions_performed"] == 0
    assert (output_dir / "fixture_results.jsonl").read_bytes() == first_results
    assert (output_dir / "failures.jsonl").read_text(encoding="utf-8") == ""
    assert "Result: PASS" in report_path.read_text(encoding="utf-8")
