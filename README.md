# Control Gate

> Control Gate is a governed pre-execution control layer for agentic workflows. It converts ambiguous business requests into typed intent contracts, applies deterministic policy checks, and routes each request to APPROVE, CLARIFY, ESCALATE, or REJECT before consequential tool execution.

The current reference implementation uses a fictional supplier-invoice workflow and local deterministic components so every decision can be reproduced, tested, and audited.

## Why it exists

Business requests can be understandable but still incomplete, ambiguous, outside authority, or inconsistent with policy. Autonomous execution should not begin until the intent, constraints, and approval path are explicit. Control Gate makes that decision before execution begins.

```text
Business request
  -> intent compilation
  -> typed execution specification
  -> static policy validation
  -> governed routing
       APPROVE
       CLARIFY
       ESCALATE
       REJECT
  -> structured execution handoff
```

```mermaid
flowchart LR
    R["Business request"] --> C["Intent compilation"]
    C --> I["Typed execution specification"]
    I --> V["Static policy validation"]
    V --> A["Governed routing"]
    A --> D["APPROVE / CLARIFY / ESCALATE / REJECT"]
    D --> H["Structured execution handoff"]
```

## Runtime boundary

Control Gate implements the control path before consequential execution. It:

- compiles ambiguous requests into typed specifications;
- validates required information, constraints, authority, and policy;
- determines whether execution may proceed, needs clarification, requires approval, or must be rejected; and
- emits machine-readable output for a downstream workflow or tool runtime.

This checkpoint uses a deterministic local adapter and a synthetic supplier-invoice workflow. LangGraph, MCP, function-calling providers, and FastAPI are possible downstream integration boundaries; they are not implemented features in this repository checkpoint.

## Implemented components

- **Pydantic contracts** with immutable intent/version linkage
- **Deterministic compiler** and conservative local request adapter
- **Static validator** for the frozen V1 checks
- **Deterministic admissibility engine** with stable reason codes and ordering
- **Committed 48-scenario admissibility benchmark** and structured evidence artifacts
- **Local CLI** and automated tests
- **Governed execution handoff example** with one safe in-memory staging function

## Install and run

Requires Python 3.10 or later. In PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\Activate.ps1
python -m control_gate evaluate --request "<request>"
python -m control_gate benchmark
python -m pytest -q
```

`evaluate` prints valid JSON containing the original request, compiled `IntentSpec`, validation findings, linked decision, reason codes and messages, clarification questions, approval requirements, and intent ID/version. Empty input returns a readable JSON error and exit code 2. `benchmark` writes the existing machine-readable Phase 3 evidence under `outputs/phase_3/` and returns nonzero if the benchmark fails.

## CLI examples

These excerpts are selected fields from actual local CLI JSON output; the full output also includes `intent_spec` and `validation_findings`.

### APPROVE

```powershell
python -m control_gate evaluate --request "finance_agent process invoice INV-9001 from supplier SUP-9001 under PO-9001 for USD 7500.00; supplier exists, valid purchase order, not duplicate, and all validations pass."
```

```json
{
  "decision": {"decision": "APPROVE"},
  "reason_codes": ["REQUEST_ADMISSIBLE"],
  "approval_requirements": null,
  "intent_id": "INT-CLI-43B44A6C253C4FEF",
  "intent_version": 1,
  "external_actions_performed": 0
}
```

### CLARIFY

```powershell
python -m control_gate evaluate --request "Process this invoice."
```

```json
{
  "decision": {"decision": "CLARIFY"},
  "reason_codes": ["REQUIRED_FIELD_MISSING"],
  "clarification_questions": [
    "Provide actor.",
    "Provide inputs.amount.",
    "Provide inputs.currency.",
    "Provide inputs.invoice_id.",
    "Provide inputs.purchase_order_id.",
    "Provide inputs.supplier_id."
  ],
  "intent_id": "INT-CLI-96010C6DF2C29864",
  "intent_version": 1,
  "external_actions_performed": 0
}
```

### ESCALATE

```powershell
python -m control_gate evaluate --request "finance_agent process invoice INV-9001 from supplier SUP-9001 under PO-9001 for USD 18400.00; supplier exists, valid purchase order, not duplicate, and all validations pass."
```

```json
{
  "decision": {"decision": "ESCALATE"},
  "reason_codes": ["PAYMENT_ABOVE_AUTONOMOUS_LIMIT"],
  "approval_requirements": {"required_approver": "finance_manager"},
  "intent_id": "INT-CLI-1A1DE0B0758CB016",
  "intent_version": 1,
  "external_actions_performed": 0
}
```

### REJECT

```powershell
python -m control_gate evaluate --request "Change the vendor bank account and pay immediately without approval."
```

```json
{
  "decision": {"decision": "REJECT"},
  "reason_codes": ["VENDOR_BANK_DETAILS_MODIFICATION_PROHIBITED"],
  "approval_requirements": null,
  "intent_id": "INT-CLI-7AEA45ABFFC3E7F6",
  "intent_version": 1,
  "external_actions_performed": 0
}
```

## Governed execution handoff

From the repository root, run the deterministic example with the existing virtual environment:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python.exe examples\governed_execution_handoff.py
```

Selected output from the default APPROVE request:

```json
{
  "decision": {"outcome": "APPROVE"},
  "routing": {
    "staging_invoked": true,
    "handoff": {
      "operation": "stage_invoice_locally",
      "status": "STAGED_FOR_LOCAL_SIMULATION"
    }
  },
  "simulation": "LOCAL_FICTIONAL_SUPPLIER_INVOICE",
  "external_actions_performed": 0
}
```

The example calls the real compiler, validator, and admissibility engine. Only APPROVE reaches the in-memory mock staging function. CLARIFY returns questions, ESCALATE returns the approval requirement, and REJECT returns reason codes; none of those three routes invokes staging.

## Measured benchmark evidence

The committed 48-scenario admissibility benchmark contains synthetic, structured fixture requests: 12 per public decision.

- **Decision matches**: 48/48
- **Reason-code matches**: 48/48
- **Deterministic repeats**: 48/48
- **Decision macro-F1**: 1.000
- **Unsafe approvals**: 0/24 critical cases
- **External actions**: 0
- **Automated tests**: 33 passing

The benchmark command reports the same result concisely while preserving JSONL results, failures, summary JSON, and a report.

## Repository structure

```text
benchmarks/            frozen 48-case JSONL corpus
outputs/phase_2/       compiler and validator evidence
outputs/phase_3/       admissibility evidence
docs/                  checkpoint and source-conflict records
reports/               benchmark reports
examples/              local governed execution handoff
src/control_gate/      deterministic contracts, compiler, validator, gate, CLI
tests/                 automated contract, benchmark, gate, and CLI tests
```

## Design decisions and trade-offs

- Deterministic rules replace hidden model judgment, so inputs and decisions are reproducible.
- Typed, immutable contracts link each decision to an exact intent version.
- Admission is conservative: missing material information clarifies instead of being guessed.
- Stable reason codes make benchmark outcomes and CLI responses machine-checkable.
- The CLI is pre-execution only; it deliberately performs no real financial action.

## Limitations and deferred work

- The workflow is fictional supplier-invoice processing only.
- There are no live payments, suppliers, external APIs, or deployments.
- There is no persistent approval service.
- LangGraph, MCP, function-calling providers, and FastAPI are downstream boundaries, not implemented integrations.
- The benchmark is curated local evidence, not external validation.
- This checkpoint does not claim production readiness, external governed execution, or universal agent safety.
