# Control Gate Source Conflicts

This record applies to the current application sprint and preserves conflicts found during the repository audit.

1. `CONTROL_GATE_KNOWLEDGE_BASE.md` describes a broader canonical domain model and a broader `IntentSpec`. `Control_Gate_Final_Application_Game_v1.md` explicitly freezes a smaller V1 contract and forbids new V1 architecture. The frozen V1 document governs implementation in this sprint; the broader knowledge-base fields remain preserved for later work.
2. The knowledge base names `ValidationFinding` and `RuntimeDecision` as first-class domain objects. The frozen V1 Phase 1 list contains exactly seven first-class contract objects and assigns validation and runtime gating to later phases. Phase 1 therefore does not promote those two objects into the frozen contract set.
3. The knowledge base lists generic human actions including `MODIFY`, `PAUSE`, and `RESUME`. The frozen V1 approval path supports exactly `APPROVE`, `DENY`, `MODIFY_CONSTRAINT`, and `CANCEL`; the V1 set governs this sprint.
4. Commit `9600049` deliberately removed Gortex-generated `AGENTS.md`, `CLAUDE.md`, and `.mcp.json` files as stale repository tooling, and commit `4a42e44` removed the remaining Gortex ignore configuration. The ignored local `.gortex` database contains no notes, notebooks, or memories. Those deleted instructions are historical evidence only and are not restored.
5. `README.md` lists an `archive/` directory that is not present in the committed tree. This documentation mismatch does not block Phase 1 and is deferred until the README phase, which must describe actual implementation.

No public identity, CV claim, portfolio material, external integration, or unrelated repository is changed by the Phase 1 milestone.
