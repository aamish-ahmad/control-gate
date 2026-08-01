# Control Gate — Canonical Knowledge Base

> **Status:** Canonical source of truth for the `control-gate` repository.  
> **Project:** Control Gate: Governed Agentic AI Runtime  
> **Year:** 2026  
> **Core principle:** **Intent before action.**

---

## 1. Canonical Definition

**Control Gate is an intent-native agentic AI control system that converts ambiguous business requests into validated, versioned execution specifications; decides whether autonomous execution should be approved, clarified, escalated, or rejected; governs the resulting workflow against that authorized contract; and records the execution as structured, observable evidence.**

The canonical lifecycle is:

```text
Request
  ↓
Compile
  ↓
Validate
  ↓
Admit
  ↓
Plan
  ↓
Execute
  ↓
Trajectory
```

The deeper primitive is:

> **Turn intent into an enforceable execution contract.**

Control Gate is not defined by the presence of agents, workflows, approvals, or traces. Those are supporting capabilities. Its defining abstraction is that **natural-language intent is compiled into a formal contract that governs what autonomous execution is allowed to do.**

---

## 2. Core Problem

Autonomous systems are frequently asked to act from requests that are:

- ambiguous;
- underspecified;
- internally conflicting;
- based on hidden assumptions;
- missing required evidence;
- outside the requester's authority;
- high impact or difficult to reverse;
- inconsistent with business policy.

A conventional agent may move directly from:

```text
Natural-language request
        ↓
Agent reasoning
        ↓
Tool call
```

Control Gate inserts a control boundary:

```text
Natural-language request
        ↓
Intent Specification
        ↓
Validation
        ↓
Admissibility
        ↓
Authorized execution contract
        ↓
Agent workflow
        ↓
Tool calls
```

The system therefore separates:

```text
what a user asked
what the system inferred
what policy permits
what execution was authorized
what the agent actually did
```

---

## 3. System Objective

Control Gate exists to answer five questions before and during autonomous execution:

1. **What is the user actually trying to accomplish?**
2. **What facts, constraints, assumptions, permissions, and evidence define that intent?**
3. **Is the intent sufficiently specified and authorized to begin execution?**
4. **Does each proposed runtime action remain consistent with the authorized intent?**
5. **What structured evidence proves what happened during the run?**

---

## 4. Intent-Native Design

In Control Gate, intent is a first-class system object.

A request such as:

> "Process this supplier invoice and pay it if everything looks correct."

is not treated as an executable instruction by itself.

It is compiled into an **Intent Specification** that makes explicit:

- the goal;
- the actor;
- the target;
- required inputs;
- required evidence;
- assumptions;
- requirements;
- constraints;
- permissions;
- prohibited actions;
- approval conditions;
- risk and impact;
- success conditions;
- failure conditions;
- reversibility or rollback conditions;
- unresolved information.

The key rule is:

> **Execution never begins directly from free-form language.**

---

## 5. Canonical System Map

```text
┌─────────────────────────────────────────────────────────────┐
│                    BUSINESS REQUEST                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. INTENT COMPILATION                                       │
│                                                             │
│ • normalize request                                         │
│ • identify goal                                             │
│ • identify actors / targets                                 │
│ • extract requirements                                      │
│ • extract constraints                                       │
│ • expose assumptions                                        │
│ • identify required evidence                                │
│ • identify permissions / authority                          │
│ • define success / failure                                  │
│ • identify unresolved fields                                │
│                                                             │
│ OUTPUT: Versioned Intent Specification                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. VALIDATION                                                │
│                                                             │
│ • schema validity                                           │
│ • completeness                                              │
│ • ambiguity                                                 │
│ • contradictions                                            │
│ • unsupported assumptions                                   │
│ • evidence sufficiency requirements                         │
│ • permission / authority requirements                       │
│ • impact / reversibility checks                             │
│                                                             │
│ OUTPUT: Structured findings                                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. ADMISSIBILITY                                             │
│                                                             │
│ Intent + Policy + Authority + Risk + Current State          │
│                                                             │
│ OUTPUT:                                                     │
│ APPROVE / CLARIFY / ESCALATE / REJECT                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. EXECUTION CONTRACT                                       │
│                                                             │
│ • approved intent version                                   │
│ • permitted actions                                         │
│ • prohibited actions                                        │
│ • required evidence                                         │
│ • approval checkpoints                                      │
│ • success / failure conditions                              │
│ • runtime constraints                                       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. AGENTIC WORKFLOW                                         │
│                                                             │
│ • LangGraph-based workflow                                  │
│ • MCP / function calling                                    │
│ • APIs / business tools                                     │
│ • retries                                                   │
│ • human-in-the-loop checkpoints                             │
│ • runtime policy enforcement                                │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. RUNTIME CONTROL                                           │
│                                                             │
│ For each proposed consequential action:                     │
│                                                             │
│ Is action a_t admissible under Intent I and state S_t?      │
│                                                             │
│ continue / clarify / escalate / reject                      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. STRUCTURED EXECUTION TRACE                               │
│                                                             │
│ • intent version                                            │
│ • decisions                                                 │
│ • state transitions                                         │
│ • agent actions                                             │
│ • tool calls                                                │
│ • policy checks                                             │
│ • retries                                                   │
│ • errors                                                    │
│ • human interventions                                       │
│ • latency / usage                                           │
│ • final outcome                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. The Two Control Gates

The name **Control Gate** refers to two logically distinct gates.

### Gate A — Pre-Execution Admissibility

Question:

> **Should this intent be allowed to begin autonomous execution?**

Conceptually:

```text
D(I, P, R, U, S) → {APPROVE, CLARIFY, ESCALATE, REJECT}
```

Where:

- `I` = Intent Specification;
- `P` = applicable policy;
- `R` = risk / impact;
- `U` = user or actor authority;
- `S` = current system state.

### Gate B — Runtime Admissibility

Question:

> **Is this proposed action still allowed by the authorized intent?**

Conceptually:

```text
D(a_t | I, P, S_t)
```

Where:

- `a_t` = proposed action at time `t`;
- `I` = immutable authorized intent version;
- `P` = active policy;
- `S_t` = current runtime state.

A run can therefore be approved initially and still be stopped or escalated later if the agent proposes an action that changes the risk, scope, authority requirement, or external impact.

---

## 7. Core Domain Objects

The canonical domain model contains the following first-class entities.

### `IntentSpec`

The formal representation of the requested and authorized intent.

### `ValidationFinding`

A structured finding produced by semantic/static validation.

### `ControlDecision`

A gate outcome:

```text
APPROVE
CLARIFY
ESCALATE
REJECT
```

### `ExecutionPlan`

The governed sequence or graph of actions required to realize an approved intent.

### `ExecutionRun`

A concrete execution instance bound to one immutable IntentSpec version.

### `RuntimeDecision`

A decision about whether a proposed action is still allowed during execution.

### `TrajectoryEvent`

A structured event representing an observable state transition, action, tool call, decision, result, or intervention.

### `HumanIntervention`

A human approval, denial, modification, pause, cancellation, or escalation decision.

### `RunOutcome`

The terminal result of the run relative to the authorized success/failure conditions.

---

## 8. Intent Specification / ISL

The **Intent Specification Language (ISL)** is the canonical intermediate representation between natural language and autonomous execution.

It is conceptually similar to an intermediate representation in a compiler:

```text
Natural Language
      ↓
Intent Compilation
      ↓
ISL / IntentSpec
      ↓
Validation
      ↓
Admissibility
      ↓
Execution
```

The important contribution is the **semantics of the contract**, not a custom textual syntax.

### Canonical IntentSpec Fields

```text
IntentSpec
├── identity
├── version
├── raw_request
├── goal
├── actors
├── targets
├── requested_actions
├── inputs
├── requirements
├── constraints
├── assumptions
├── evidence_requirements
├── permissions
├── authority
├── prohibited_actions
├── approval_rules
├── risk
├── impact
├── reversibility
├── success_conditions
├── failure_conditions
├── rollback_conditions
└── unresolved_fields
```

---

## 9. Intent Identity and Versioning

Every intent has:

- a stable intent identity;
- one or more versions;
- immutable historical versions.

Example:

```text
INT-872 v1
INT-872 v2
INT-872 v3
```

A run is always bound to the exact version that authorized it:

```text
ExecutionRun → IntentSpec(version=N)
```

A later change to the intent must never retroactively change the meaning of an earlier run.

This is required for:

- auditability;
- reproducibility;
- accountability;
- intent diffing;
- historical explanation.

---

## 10. Intent Diff

Control Gate treats a change in intent as a first-class event.

Example:

### Version 1

```text
Read the customer's transaction history.
```

### Version 2

```text
Read the customer's transaction history
and refund suspicious charges.
```

### Semantic Diff

```text
NEW ACTION:
external financial action

NEW IMPACT:
money can leave the organization

NEW AUTHORITY REQUIREMENT:
refund permission required

NEW REVERSIBILITY PROPERTY:
financial action may require recovery

CONTROL CONSEQUENCE:
decision may change from APPROVE to ESCALATE
```

An Intent Diff is not merely a textual diff. It captures **semantic changes in action, risk, authority, evidence, constraints, and impact**.

---

## 11. Assumptions

Control Gate must preserve a strict distinction between:

```text
explicit user instruction
```

and:

```text
system/model inference
```

Assumptions are therefore first-class fields.

Examples:

```text
"everything looks correct"
```

may silently imply assumptions about:

- what evidence counts as correct;
- which source is authoritative;
- which policy applies;
- what amount is allowed;
- who may approve the action.

Assumptions that materially affect consequential execution must be surfaced before action.

---

## 12. Requirements and Constraints

### Requirements

Things that **must happen**.

Example:

```text
verify vendor
match purchase order
check duplicate invoice
record transaction
```

### Constraints

Things that **must remain true**.

Example:

```text
vendor must already exist
payment must not exceed autonomous limit
currency must be supported
external notification must not expose sensitive fields
```

A request can have valid requirements but still be inadmissible because a critical constraint is absent or violated.

---

## 13. Evidence Requirements

Consequential actions may require evidence before execution.

Example:

```text
Action:
issue refund

Required evidence:
- order exists
- payment exists
- complaint is verified
- refund was not already issued
```

Evidence requirements are part of the authorized contract.

The execution is not considered valid merely because the model believes the action is appropriate.

---

## 14. Permissions and Authority

Control Gate distinguishes:

```text
the user wants this
```

from:

```text
the user is authorized to request this
```

and:

```text
the agent is authorized to perform this
```

Authority can be action-specific and threshold-specific.

Example:

```text
refund <= $50:
autonomous

refund $51–$500:
manager approval

refund > $500:
not permitted under current authority
```

Authority is therefore part of admissibility, not merely part of execution.

---

## 15. Risk, Impact, and Reversibility

Every consequential intent or action may be characterized by:

- impact domain;
- magnitude;
- external side effects;
- financial consequence;
- data consequence;
- communication consequence;
- operational consequence;
- reversibility;
- recovery cost;
- approval requirement.

A request that only reads data is different from a request that:

- sends an external email;
- modifies a record;
- issues a refund;
- submits a payment;
- deletes data.

The system must preserve that distinction throughout the run.

---

## 16. Validation Model

Validation is not binary schema validation alone.

It produces structured findings across multiple semantic classes.

### Completeness

Does the intent contain enough information to execute responsibly?

Examples:

- target missing;
- amount missing;
- scope missing;
- decision criterion missing;
- success condition missing;
- required authority unresolved.

### Ambiguity

Does wording admit materially different interpretations?

Examples:

```text
"if appropriate"
"if it looks valid"
"handle the issue"
"send it to them"
```

Ambiguity becomes especially important when attached to a consequential action.

### Contradictions

Examples:

```text
"Never contact the customer."
```

and:

```text
"Email the customer when complete."
```

### Unsupported Assumptions

The system inferred a material fact that was not authorized or grounded.

### Evidence Gaps

A required decision cannot be made from currently available evidence.

### Permission / Authority Gaps

The requested action is understood but the current actor does not have sufficient authority.

### High-Impact / Reversibility Findings

The request contains actions whose consequences require stronger control.

---

## 17. Admissibility Decisions

The control alphabet is fixed:

```text
APPROVE
CLARIFY
ESCALATE
REJECT
```

### APPROVE

The intent is sufficiently specified, evidence requirements are satisfiable, and the requested execution falls within current authority and policy.

Meaning:

```text
execution may begin
```

### CLARIFY

The intent may be valid, but required information is missing or materially ambiguous.

Meaning:

```text
request additional information before execution
```

Example:

```text
"Refund the customer if the complaint looks valid."
```

Possible missing fields:

- transaction;
- refund limit;
- definition of valid complaint;
- required evidence.

### ESCALATE

The request is understood, but execution requires a higher-authority decision.

Meaning:

```text
human authorization required
```

Typical causes:

- financial threshold exceeded;
- consequential external action;
- policy requires approval;
- exceptional case;
- conflicting objectives requiring human judgment.

### REJECT

The requested execution conflicts with a hard policy, permission boundary, prohibited action, or non-negotiable constraint.

Meaning:

```text
execution must not proceed
```

---

## 18. Structured Decision Reasons

Every ControlDecision must be explainable through structured reasons.

Example:

```json
{
  "decision": "CLARIFY",
  "reasons": [
    "refund_limit_missing",
    "validation_criterion_undefined"
  ],
  "questions": [
    "What refund amount may be authorized?",
    "What evidence establishes a valid complaint?"
  ]
}
```

A decision must never be only an opaque label.

---

## 19. Policy Semantics

Intent and policy are separate objects.

Example:

```text
Intent:
Pay this invoice.

Policy:
Payments above $10,000 require finance-manager approval.
```

Admissibility is therefore determined from:

```text
Intent
+
Policy
+
Authority
+
Risk
+
Current State
```

The policy constrains execution; the model does not invent the policy.

---

## 20. Execution Contract

An approved IntentSpec becomes an **execution contract**.

The contract defines:

- what goal is authorized;
- which intent version authorized the run;
- what actions are allowed;
- which actions are prohibited;
- what evidence is required;
- what authority exists;
- what constraints remain active;
- when approval is required;
- what counts as success;
- what counts as failure;
- which runtime changes require re-adjudication.

The runtime is governed by this contract for the entire execution.

---

## 21. Planning Semantics

An approved intent is transformed into an executable plan.

A plan contains:

- steps;
- dependencies;
- state transitions;
- required tools;
- required evidence;
- approval checkpoints;
- success conditions;
- failure paths;
- permissible retries;
- terminal states.

Conceptually:

```text
IntentSpec
    ↓
ExecutionPlan
    ↓
Agentic Workflow
```

A plan is always subordinate to the authorized IntentSpec.

The plan may operationalize an intent, but it may not silently expand its scope.

---

## 22. Agentic Runtime

Control Gate executes multi-step business workflows using a LangGraph-based runtime.

The runtime supports:

- stateful execution;
- agent logic;
- tool/function calling;
- MCP interactions;
- API interactions;
- conditional branches;
- retries;
- human-in-the-loop pauses;
- continuation after approval;
- execution tracing.

The runtime is not allowed to treat successful tool execution as proof that the original intent was satisfied.

Success is determined relative to the contract.

---

## 23. Runtime State Machine

A run has explicit lifecycle states.

Canonical states:

```text
CREATED
   ↓
COMPILING
   ↓
VALIDATING
   ↓
AWAITING_DECISION
```

Possible branch:

```text
CLARIFICATION_REQUIRED
ESCALATION_REQUIRED
REJECTED
```

Approved branch:

```text
APPROVED
   ↓
PLANNED
   ↓
RUNNING
```

During execution:

```text
WAITING_FOR_HUMAN
RUNNING
```

Terminal states:

```text
COMPLETED
FAILED
CANCELLED
REJECTED
ROLLED_BACK
```

State transitions are part of the execution evidence.

---

## 24. Runtime Admissibility

Approval at time `t0` does not grant unlimited permission for all later actions.

Every consequential proposed action must remain consistent with:

- the authorized IntentSpec;
- active policy;
- current authority;
- current state;
- current risk;
- accumulated execution evidence.

Example:

```text
Authorized intent:
review account

Later proposed action:
issue refund
```

The new action introduces:

```text
financial impact
new permission requirement
new approval requirement
```

The runtime gate can therefore escalate or block the proposed action even though the run itself was previously approved.

---

## 25. Human-in-the-Loop Control

Human intervention is a first-class control mechanism.

Possible human actions include:

```text
APPROVE
DENY
MODIFY
PAUSE
RESUME
CANCEL
```

A human checkpoint may be triggered because:

- authority threshold is exceeded;
- a material ambiguity appears at runtime;
- evidence conflicts;
- the proposed action changes scope;
- policy requires explicit approval;
- risk becomes higher than originally authorized.

Human decisions must become structured events in the run.

---

## 26. Retries

Retries are part of the governed execution semantics.

A retry must preserve:

- the active intent version;
- the original constraints;
- the same authorization boundary;
- the reason for retry;
- retry count;
- resulting state.

Retries may not become an implicit mechanism for bypassing an earlier failed control decision.

---

## 27. Tool and Function Calls

A tool call is an action with:

- a tool identity;
- arguments;
- expected effect;
- state before execution;
- policy checks;
- authorization status;
- result;
- state after execution;
- side-effect classification.

Tool calls can be distinguished by effect:

```text
READ
DRAFT
WRITE
SEND
MODIFY
DELETE
TRANSFER
APPROVE
```

Consequential tool calls require stronger admissibility than read-only operations.

---

## 28. Structured Execution Trajectory

Every run produces a structured trajectory.

Conceptually:

```text
τ = (s0, a0, e0, s1, a1, e1, ... , sT)
```

The trajectory preserves:

```text
original request
intent identity
intent version
compiled specification
validation findings
control decisions
execution plan
state transitions
agent actions
tool calls
tool arguments
tool results
policy decisions
retries
errors
human interventions
latency
usage
outcome
```

The trajectory is **structured execution evidence**, not a transcript dump.

---

## 29. No Hidden Chain-of-Thought Requirement

Control Gate does not require or depend on storing private chain-of-thought.

The relevant evidence is observable and structured:

```text
decision
action
tool
arguments
state
observation
policy check
result
human intervention
outcome
```

This is sufficient to inspect and audit execution behavior.

---

## 30. Canonical Trajectory Event

A trajectory event can be represented conceptually as:

```json
{
  "event_id": "evt_1837",
  "run_id": "run_927",
  "intent_id": "int_872",
  "intent_version": 2,
  "timestamp": "...",
  "step_id": "validate_po",
  "actor": "invoice_agent",
  "event_type": "tool_call",
  "tool": "erp.lookup_po",
  "state_before": "PO_PENDING",
  "state_after": "PO_MISMATCH",
  "policy_checks": [],
  "status": "completed",
  "latency_ms": 428
}
```

A human intervention event might contain:

```json
{
  "event_type": "human_intervention",
  "reason": "approval_threshold_exceeded",
  "available_actions": [
    "approve",
    "deny",
    "modify"
  ],
  "selected_action": "approve"
}
```

---

## 31. Run Outcome

A run outcome is not simply:

```text
status = success
```

A successful run must satisfy the IntentSpec's explicit success conditions.

Example:

```text
Goal:
process invoice

Success conditions:
- vendor validated
- purchase order matched
- duplicate check passed
- required approval obtained
- transaction recorded
- final state persisted
```

A model saying "Done" is not evidence of success.

---

## 32. Failure Model

Control Gate distinguishes different failure classes.

### Compilation Failure

The request cannot be converted into a coherent intent.

### Validation Failure

The specification is malformed, contradictory, materially ambiguous, or incomplete.

### Admissibility Failure

The intent is validly understood but cannot currently be authorized.

### Planning Failure

An approved intent cannot be converted into a valid executable plan.

### Tool / Integration Failure

A required external capability fails.

### Runtime Policy Failure

A proposed action violates the active execution contract.

### Human Rejection

A human denies or modifies a proposed action.

### Outcome Failure

Execution completes technically but fails to satisfy the authorized success criteria.

These distinctions should remain observable in traces and evaluation.

---

## 33. Core Safety / Control Invariants

The following invariants define correct Control Gate behavior.

### Invariant 1 — No Direct Execution from Raw Intent

```text
raw_request ≠ execution_authority
```

A natural-language request must be compiled and adjudicated first.

### Invariant 2 — Every Run Has an Authorizing Intent Version

```text
ExecutionRun → exactly one authorized IntentSpec version
```

### Invariant 3 — Assumptions Are Not Equivalent to User Instructions

Material inferred assumptions must remain distinguishable from explicit requirements.

### Invariant 4 — Runtime Actions Cannot Expand Intent Silently

A proposed action outside the authorized scope requires re-adjudication.

### Invariant 5 — High-Impact Actions Require Appropriate Authority

Consequential effects cannot be justified solely by model confidence.

### Invariant 6 — Human Decisions Change Runtime State

An approval, denial, modification, pause, or cancellation must materially alter what execution is allowed to do.

### Invariant 7 — Policy Is External to Model Preference

Policy is a constraint on execution, not something the model may reinterpret opportunistically.

### Invariant 8 — Success Is Contract-Relative

A run succeeds only if the authorized success criteria are satisfied.

### Invariant 9 — Every Consequential Action Is Traceable

The system must preserve enough structured evidence to explain what action occurred, under which intent, with which authority, and with what result.

---

## 34. Canonical Business Demonstration

The primary business example is **supplier invoice processing**.

### User Request

> "Process this supplier invoice and pay it if everything looks correct."

### Compiled Intent

```text
Goal:
process supplier invoice

Requirements:
- extract invoice details
- verify vendor
- retrieve purchase order
- match invoice to purchase order
- check for duplicate invoice
- evaluate payment conditions

Constraints:
- vendor must be recognized
- invoice must not be duplicate
- payment must remain within authorized rules

Required evidence:
- invoice
- vendor record
- purchase order
- payment status

Success:
- invoice validated
- required approval obtained
- transaction recorded
- audit event written

Possible failures:
- vendor mismatch
- duplicate invoice
- PO mismatch
- insufficient authority
- tool failure
```

### Example Admissibility Cases

#### Case A — Fully Specified and Authorized

```text
Decision:
APPROVE
```

#### Case B — Undefined Criteria

```text
"Pay it if everything looks correct."

Critical decision criteria unresolved.

Decision:
CLARIFY
```

#### Case C — Amount Exceeds Authority

```text
Amount:
$18,400

Autonomous authority:
below required threshold

Decision:
ESCALATE
```

#### Case D — Hard Policy Conflict

```text
Requested action violates non-negotiable policy.

Decision:
REJECT
```

---

## 35. Canonical Evaluation Set

The evaluation corpus should represent the kinds of business requests Control Gate claims to govern.

Scenario classes:

```text
clear and authorized
ambiguous
underspecified
missing constraints
missing evidence
conflicting requirements
unsupported assumptions
unauthorized
approval-required
high impact
policy violating
scope mutation
runtime policy conflict
```

Each scenario has an expected gate outcome:

```text
APPROVE
CLARIFY
ESCALATE
REJECT
```

and expected structured reasons.

---

## 36. Core Evaluation Metrics

### Intent Field Accuracy

Measures whether the compiler recovered the expected intent fields.

### Specification Completeness

Measures whether required contract fields are present.

### Clarification Precision

```text
necessary clarification questions
--------------------------------
all clarification questions
```

Measures whether Control Gate avoids asking irrelevant questions.

### Clarification Recall

Measures whether important missing information is actually detected.

### Admissibility Accuracy

Measures agreement between predicted and expected:

```text
APPROVE
CLARIFY
ESCALATE
REJECT
```

### Unsafe Approval Rate

```text
unsafe intents incorrectly approved
-----------------------------------
all unsafe intents
```

This is a critical control metric.

### Unnecessary Blocking Rate

Measures safe/authorized requests incorrectly prevented from executing.

### Policy Adherence

Measures whether runtime actions remain consistent with the active contract and policy.

### Execution Success

Measures whether approved workflows satisfy their explicit success conditions.

### Runtime Contract Violation Rate

Measures proposed or executed actions that deviate from the authorized IntentSpec.

---

## 37. Ungated Baseline

The central comparison is:

### Ungated Agent

```text
Request
  ↓
Agent
  ↓
Tool
```

### Control Gate

```text
Request
  ↓
IntentSpec
  ↓
Validation
  ↓
Admissibility
  ↓
Agent
  ↓
Runtime Control
  ↓
Tool
```

The evaluation compares systems on outcomes such as:

```text
invalid actions
missing-information executions
unsafe approvals
correct escalations
policy adherence
successful workflows
```

The purpose is to measure whether the gate produces materially safer and more reliable execution rather than merely adding architecture.

---

## 38. Observable Run Summary

A completed run can expose a concise summary such as:

```text
Intent:
Process Supplier Invoice

Intent Version:
2

Initial Decision:
ESCALATE

Execution:
COMPLETED

Steps:
11

Tool Calls:
7

Human Interventions:
2

Retries:
1

Policy Violations Prevented:
1

Outcome:
SUCCESS
```

The summary is derived from structured run evidence.

---

## 39. Service Surface

Control Gate is an executable system rather than a notebook-only experiment.

Its external service concept exposes the lifecycle of a governed run:

```text
compile intent
validate intent
adjudicate intent
execute approved intent
inspect run
approve / deny escalated action
inspect trajectory
```

The public service behavior must preserve the same canonical semantics described in this knowledge base.

---

## 40. Control Gate Identity Boundaries

Control Gate should never be reduced to any one of these descriptions:

```text
"an AI agent"
"a workflow engine"
"a prompt parser"
"a policy engine"
"a guardrail"
"a monitoring dashboard"
"a trace viewer"
```

Each description captures only a surface capability.

The correct identity is:

> **A governed agentic AI runtime built around a formal, enforceable execution contract derived from business intent.**

---

## 41. Canonical Product One-Liners

### Primary

> **Prevent underspecified or unauthorized intent from becoming autonomous action.**

### Technical

> **Compile business intent into a validated execution contract, then govern agent actions against that contract.**

### Enterprise

> **A governed agentic AI runtime for turning ambiguous business requests into controlled, observable multi-step execution.**

---

## 42. Repository Name and Public Identity

### Repository

```text
control-gate
```

### Project Name

```text
Control Gate
```

### CV Name

```text
Control Gate: Governed Agentic AI Runtime
```

### README Title

```text
Control Gate — Intent-Native Control for Agentic AI
```

---

## 43. CV Contract

The following is the canonical CV representation and must remain supported by visible repository evidence.

### Control Gate: Governed Agentic AI Runtime — 2026

**GitHub**

- Built an **intent-native agentic AI control layer** that converts ambiguous business requests into validated execution specifications and gates autonomous actions through **APPROVE / CLARIFY / ESCALATE / REJECT** decisions before tool execution.
- Engineered **LangGraph-based workflows with MCP/function calling, human-in-the-loop approvals, policy enforcement, retries, and execution tracing** for reliable multi-step business automation.
- Developed and evaluated safeguards for **underspecified, conflicting, unauthorized, and high-risk requests**, with **FastAPI services, automated tests, and observable execution traces**.

---

## 44. CV Claim → System Capability Map

### Claim 1

> Converts ambiguous business requests into validated execution specifications.

Required system meaning:

```text
Natural language
→ Intent Compiler
→ IntentSpec
→ semantic/static validation
```

### Claim 1

> Gates autonomous actions through APPROVE / CLARIFY / ESCALATE / REJECT.

Required system meaning:

```text
structured ControlDecision
+
structured reasons
+
clarification/escalation behavior
```

### Claim 2

> LangGraph-based workflows.

Required system meaning:

```text
stateful multi-step execution
+
conditional transitions
+
governed runtime state
```

### Claim 2

> MCP/function calling.

Required system meaning:

```text
actual tool invocation
+
structured arguments/results
+
tool calls represented in execution evidence
```

### Claim 2

> Human-in-the-loop approvals.

Required system meaning:

```text
runtime pause
+
human decision
+
decision changes allowed execution state
```

### Claim 2

> Policy enforcement.

Required system meaning:

```text
pre-execution policy evaluation
+
runtime action checks
```

### Claim 2

> Retries.

Required system meaning:

```text
observable retry reason
+
retry count
+
preserved intent constraints
```

### Claim 2

> Execution tracing.

Required system meaning:

```text
structured run events
+
state transitions
+
tool calls
+
control decisions
+
outcome
```

### Claim 3

> Safeguards for underspecified requests.

Required system meaning:

```text
completeness checks
+
CLARIFY behavior
```

### Claim 3

> Safeguards for conflicting requests.

Required system meaning:

```text
contradiction detection
+
structured finding
```

### Claim 3

> Safeguards for unauthorized requests.

Required system meaning:

```text
authority / permission evaluation
+
ESCALATE or REJECT
```

### Claim 3

> Safeguards for high-risk requests.

Required system meaning:

```text
impact / risk / reversibility analysis
+
stronger approval requirements
```

### Claim 3

> Developed and evaluated.

Required system meaning:

```text
labeled scenario set
+
metrics
+
baseline comparison
+
reported results
```

### Claim 3

> FastAPI services.

Required system meaning:

```text
externally callable governed-run lifecycle
```

### Claim 3

> Automated tests.

Required system meaning:

```text
repeatable behavioral and system checks
```

### Claim 3

> Observable execution traces.

Required system meaning:

```text
inspectable structured run evidence
```

---

## 45. System Completeness Contract

Control Gate is conceptually complete only when the system can demonstrate the entire lifecycle:

```text
ambiguous request
        ↓
versioned IntentSpec
        ↓
semantic validation
        ↓
structured gate decision
        ↓
execution contract
        ↓
stateful agentic workflow
        ↓
tool/function calls
        ↓
runtime control
        ↓
human approval where required
        ↓
retries / errors where applicable
        ↓
terminal outcome
        ↓
structured observable trace
```

and when the gate itself has measurable evaluation evidence across the request categories it claims to handle.

---

## 46. Canonical Mental Model

A conventional agent system can be simplified as:

```text
x → π → a
```

where:

- `x` = request/context;
- `π` = agent policy;
- `a` = action.

Control Gate inserts a governed contract:

```text
x
↓
I
↓
C
↓
P
↓
A1:T
```

where:

- `I` = Intent Specification;
- `C` = control/admissibility decision;
- `P` = authorized execution plan;
- `A1:T` = realized action sequence.

This creates a direct comparison between:

```text
AUTHORIZED BEHAVIOR
vs.
OBSERVED BEHAVIOR
```

That comparison is the foundation for judging whether the runtime remained faithful to the authorized business intent.

---

## 47. Intent Alignment Concept

A natural system-level metric is:

```text
Intent Alignment = f(IntentSpec, ExecutionTrajectory)
```

The question is:

> **How closely did the realized execution remain within the actions, constraints, authority, evidence requirements, and success conditions authorized by the intent contract?**

This concept should remain grounded in observable execution behavior rather than hidden reasoning.

---

## 48. Agent Interpretation Rules

Any agent reading this repository should preserve the following interpretation.

### Rule 1

The main innovation is **not agent orchestration**.

It is:

```text
natural language
→ formal intent
→ admissibility
→ enforceable runtime contract
```

### Rule 2

`APPROVE / CLARIFY / ESCALATE / REJECT` are semantic control outcomes, not generic status codes.

### Rule 3

An IntentSpec is an authorization contract, not merely an extraction schema.

### Rule 4

A run is permanently linked to the exact IntentSpec version that authorized it.

### Rule 5

Runtime control is as important as pre-execution control.

### Rule 6

A tool succeeding technically does not prove the business intent succeeded.

### Rule 7

Human approval is meaningful only when it changes what execution is permitted to do.

### Rule 8

Structured trajectory evidence is required to explain the run.

### Rule 9

The system must distinguish user instruction, model inference, policy, authority, and runtime observation.

### Rule 10

Do not expand the project identity into a generic "AI platform." Always anchor explanations in the execution-contract primitive.

---

## 49. Glossary

### Intent

The business goal and conditions the requester wants realized.

### Intent Compiler

The component that transforms a natural-language request into an IntentSpec.

### ISL

Intent Specification Language: the structured representation of authorized AI intent.

### IntentSpec

A concrete versioned instance of ISL.

### Validation

Analysis of completeness, ambiguity, contradictions, assumptions, evidence requirements, permissions, and risk.

### Admissibility

The decision about whether and under what conditions execution may proceed.

### APPROVE

Execution may proceed under the current contract.

### CLARIFY

Required information is missing or materially ambiguous.

### ESCALATE

The intent is understood but needs higher authority or human judgment.

### REJECT

The requested execution conflicts with a hard boundary.

### Execution Contract

The active authorized IntentSpec plus the constraints that govern the run.

### Runtime Admissibility

Evaluation of a proposed action against the active execution contract and current state.

### Human Intervention

A structured human decision that changes or confirms allowed execution.

### ExecutionRun

One concrete governed execution instance.

### TrajectoryEvent

A structured observable event generated during a run.

### Execution Trajectory

The ordered sequence of states, actions, decisions, tool calls, observations, interventions, and outcomes.

### Intent Diff

A semantic comparison between IntentSpec versions.

### Intent Alignment

The degree to which observed execution remains faithful to the authorized intent contract.

---

## 50. Final Canonical Statement

> **Control Gate is a governed agentic AI runtime built around an intent-native execution contract. It compiles ambiguous business requests into versioned Intent Specifications, validates assumptions, constraints, evidence requirements, permissions and risk, and determines whether execution should be APPROVED, CLARIFIED, ESCALATED or REJECTED. Approved intents become enforceable execution contracts for LangGraph-based workflows using MCP/function calling, APIs and human approval checkpoints. During execution, consequential actions are continuously checked against the authorized intent and active policy. Every control decision, state transition, tool call, retry, error, human intervention and outcome is preserved as structured execution evidence, allowing the system to demonstrate not merely that an agent ran, but that it acted within the intent it was actually authorized to execute.**

---

# Canonical Formula

```text
REQUEST
  ↓
INTENT
  ↓
CONTRACT
  ↓
CONTROL
  ↓
EXECUTION
  ↓
EVIDENCE
```

Or in the project’s original lifecycle form:

```text
Request → Compile → Validate → Admit → Plan → Execute → Trajectory
```

And the governing principle remains:

> **Intent before action.**
