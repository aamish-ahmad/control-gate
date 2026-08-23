"""Tests for metamorphic testing layer."""

from __future__ import annotations

from collections import defaultdict

from control_gate.admissibility import decide
from control_gate.compiler import FixtureCompiler
from control_gate.fixtures import build_frozen_request_benchmark
from control_gate.metamorphic import generate_metamorphic_cases


def test_metamorphic_parity_and_boundaries() -> None:
    fixtures = build_frozen_request_benchmark()
    cases = []

    for fixture in fixtures:
        cases.extend(list(generate_metamorphic_cases(fixture)))

    assert len(cases) > 0, "Should generate metamorphic cases"

    failures = []
    relations = defaultdict(int)
    proves_statements = {}
    compiler = FixtureCompiler()

    for case in cases:
        relations[case.mutation_type] += 1
        proves_statements[case.mutation_type] = case.proves

        try:
            intent = compiler.compile(case.mutated_fixture)
            result = decide(intent)

            if result.decision != case.expected_decision:
                failures.append(f"Case {case.original_fixture_id} ({case.mutation_type}): Expected {case.expected_decision}, got {result.decision}.")

            if case.expected_reason_codes != result.reason_codes:
                failures.append(f"Case {case.original_fixture_id} ({case.mutation_type}): Expected reason {case.expected_reason_codes}, got {result.reason_codes}.")

        except Exception as e:
            failures.append(f"Case {case.original_fixture_id} ({case.mutation_type}): Exception {str(e)}.")

    print(f"\nGenerated {len(cases)} metamorphic cases.")
    for relation, count in relations.items():
        print(f"- {relation}: {count} cases. Proves: {proves_statements[relation]}")

    if failures:
        print(f"Failures ({len(failures)}):")
        for f in failures[:10]:
            print(f"  {f}")

    assert len(failures) == 0, f"Found {len(failures)} failures in metamorphic relations."
