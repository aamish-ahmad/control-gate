# Control Gate Source Conflicts

This record applies to the current application sprint and preserves conflicts found during the repository audit.

1. `docs/internal/knowledge-base.md` describes a broader canonical domain model and a broader `IntentSpec`. `docs/internal/application-plan.md` explicitly freezes a smaller V1 contract and forbids new V1 architecture. The frozen V1 document governs implementation in this sprint; the broader knowledge-base fields remain preserved for later work.
2. The knowledge base names `ValidationFinding` and `RuntimeDecision` as first-class domain objects. The frozen V1 Phase 1 list contains exactly seven first-class contract objects and assigns validation and runtime gating to later phases. Phase 1 therefore does not promote those two objects into the frozen contract set.
3. The knowledge base lists generic human actions including `MODIFY`, `PAUSE`, and `RESUME`. The frozen V1 approval path supports exactly `APPROVE`, `DENY`, `MODIFY_CONSTRAINT`, and `CANCEL`; the V1 set governs this sprint.
4. Commit `9600049` deliberately removed Gortex-generated `AGENTS.md`, `CLAUDE.md`, and `.mcp.json` files as stale repository tooling, and commit `4a42e44` removed the remaining Gortex ignore configuration. The ignored local `.gortex` database contains no notes, notebooks, or memories. Those deleted instructions are historical evidence only and are not restored.
5. `README.md` lists an `archive/` directory that is not present in the committed tree. This documentation mismatch does not block Phase 1 and is deferred until the README phase, which must describe actual implementation.

No public identity, CV claim, portfolio material, external integration, or unrelated repository is changed by the Phase 1 milestone.

6. The frozen source defines a logical 48-request benchmark and exact 12/12/12/12 decision balance, but no serialized corpus exists in the working tree or Git history. The partial Phase 2 catalog is a transparent local instantiation and must not be described as a recovered pre-existing dataset.

11. Item 9 is superseded by the committed Phase 2 evidence at 179513e. The
    source still has no numerical Phase 2 threshold, so the repository uses
    the recorded structural checkpoint rather than claiming a source metric.
12. The source lacks total simultaneous-finding precedence. Phase 3 records a
    narrow deterministic precedence in docs/internal/decisions.md and validates it against
    the persisted fixture corpus; it is not claimed as a source-defined
    universal policy.

7. The frozen source provides no complete static-finding or decision reason-code taxonomy and no total precedence for simultaneous findings. Only PAYMENT_ABOVE_AUTONOMOUS_LIMIT is exemplified. Local stable codes and any precedence must be recorded as implementation decisions.
8. For a payment above USD 10,000 with a missing approval rule, the frozen source explicitly permits CLARIFY or ESCALATE. Fixture CG-CLR-12 selects CLARIFY; this does not establish a global source-defined precedence.
9. The frozen source does not state a numerical Phase 2 pass threshold. Phase 2 remains incomplete until formal tests, a committed JSONL corpus, generated outputs, and the Phase 2 report exist.
10. The frozen source describes a live-provider compiler path, while the current user instruction requires the deterministic offline compiler to be the V1 evaluation reference and forbids external model dependence. Only the deterministic partial path is implemented; live-provider work is deferred and no model call occurred.

13. Item 5 is resolved by the runnable checkpoint README: it no longer lists a
    non-existent `archive/` directory and describes only tracked repository
    structure and measured local behavior.
14. The frozen V1 document also describes runtime execution, LangGraph, MCP,
    and API work. This checkpoint is intentionally limited to the separately
    authorized deterministic pre-execution CLI; those later features are
    neither implemented nor claimed.
