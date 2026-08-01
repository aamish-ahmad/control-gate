# Phase 2 compiler and validator report

Result: PASS

- Fixtures: 48
- Decision distribution: {"APPROVE": 12, "CLARIFY": 12, "ESCALATE": 12, "REJECT": 12}
- Compilation success: 48
- Schema-valid intents: 48
- Exact static-finding agreement: 48
- Deterministic repeats: 48
- False positives: 0
- False negatives: 0
- External actions: 0
- Fixture SHA-256: 4db513e6798f8975ad04aec3c457eeca0ec401d2cc1f02e2d63ce8f7d843f503

| Integrity check | Result |
|---|---|
| total_is_48 | PASS |
| balanced_decisions | PASS |
| fixture_ids_unique | PASS |
| requests_unique | PASS |
| required_categories_covered | PASS |
| schema_version_is_v1 | PASS |

The fixture corpus was locally instantiated because no serialized corpus was
present in the repository or its history. The labels and expected findings are
loaded and evaluated without automatic relabeling.
