# Control Gate Decisions

## D-001 — Frozen V1 source precedence

For the current sprint, docs/internal/application-plan.md governs when
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


## D-008 — Phase 2 evidence satisfies the structural checkpoint

The persisted 48-case corpus, formal tests, deterministic rerun, outputs, and
report satisfy the documented Phase 2 structural checkpoint. This does not
claim a source-defined numerical Phase 2 threshold.

## D-009 — Phase 3 precedence is narrow and fixture-bound

Pre-execution rejection takes precedence for frozen policy conflicts, unsafe
assumptions, non-reversible high-impact actions, explicit wildcard permissions,
and irreconcilable submit/do-not-submit requirements. Material incompleteness,
ambiguity, missing approval routing, currency contradiction, no-tool unbounded
permission, and missing success conditions clarify. A complete request above
the autonomous limit escalates to finance_manager; otherwise it approves.
Reason selection is stable and uses the recorded precedence order. This choice
implements the persisted fixtures and is not a general authorization engine.

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

## D-010 — The local CLI is explicit-only and pre-execution

The runnable CLI uses deterministic local phrase extraction as an adapter to
the existing fixture compiler. It accepts only explicit supplier-invoice
identifiers, amounts, a `finance_agent` actor marker, and selected policy
phrases; it does not call an LLM or infer missing material facts. This keeps
the command reproducible and conservative at the cost of a deliberately narrow
natural-language surface. It returns a decision only and never invokes a tool
or business action.
