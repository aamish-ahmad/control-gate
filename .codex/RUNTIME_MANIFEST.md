# Control Gate Runtime Manifest

Project: Control Gate V2 Closure
Execution branch: v2-closure-execution
Frozen baseline main SHA: 6c48d6449080b0e036025cb305b2c590b00737a4
Notion control page: 04 — Control Gate V2 — Closure Spec
Notion page ID: 3c0d086d-0fe9-81ec-9e0f-c28b316836e1

## Required generic global skills
- trajectory-alignment-controller
- transition-commit-gate
- trajectory-resource-router
- trajectory-prompt-compiler
- bounded-executor
- independent-verifier

If an equivalent controller skill is present under another name, do not substitute project state from another repository. Control Gate state must come from this repo + the frozen Notion contract.

## User interaction
- START = execute only the current next legal transition.
- DONE = phase shared checkpoint exists; ChatGPT/controller can inspect Notion + GitHub.
- BLOCKED = persist available evidence and stop.

## Invariants
- Preserve existing V1 deterministic semantics unless a bounded phase explicitly authorizes a change and regression evidence passes.
- Preserve the 48-case benchmark unchanged.
- GitHub/shared artifacts are required for handoff; unpushed local state is insufficient.
- No automatic merge to main.
