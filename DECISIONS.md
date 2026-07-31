# Control Gate Decisions

## D-001 — Frozen V1 source precedence

For the current sprint, Control_Gate_Final_Application_Game_v1.md governs when
it conflicts with the broader knowledge base. This preserves the smaller V1
use case, seven first-class contracts, exact enums, and bounded hard gates.

## D-002 — Deep immutability is part of version integrity

ConfigDict(frozen=True) did not prevent in-place mutation of nested JSON. The
verified recovery checkpoint recursively freezes contract mappings and lists
while preserving ordinary JSON serialization. A semantic modification must
therefore produce a new intent version rather than mutate an existing
authorizing object.

## D-003 — Deterministic fixture compiler is the evaluation reference

The current compiler is offline and reads only the request fixture plus its
structured context. It performs no model, network, tool, or business action.
A live-provider compiler path is not implemented in this partial milestone.

## D-004 — Validation codes map to the eleven frozen checks

Static findings use eleven stable V_* families, one per check named in the
frozen static-validation section. Finding severity is BLOCKING; the later
admissibility engine, not the validator, must map findings to public decisions.

## D-005 — Missing corpus is instantiated transparently

No serialized 48-case corpus existed in the repository or Git history. The
partial implementation defines an auditable in-memory catalog with the frozen
12/12/12/12 balance and coverage tags. It is not yet a committed JSONL
benchmark and Phase 2 is not complete.

## D-006 — Missing approval rule fixture selects CLARIFY

For the documented high-value case with no approval rule, the source permits
CLARIFY or ESCALATE. Fixture CG-CLR-12 selects CLARIFY because the candidate
contract lacks material approval routing. This local choice is not presented
as a source-defined global precedence rule.

## D-007 — No Phase 2 pass claim without persisted evidence

Because the source provides no numerical Phase 2 threshold, the intended local
checkpoint will require all 48 fixtures to compile, validate against the exact
schema, repeat deterministically, match reviewed expected finding families,
and perform zero external actions. That checkpoint has not yet been run or
persisted.
