# Intent Transition Gate

**A runnable transition controller for human-directed AI agents.** It decides when an authorized proposed action should **PROCEED**, when to **PROBE** for more evidence, when to **GATE** for a human decision, and when to **STOP**.

**Core idea:** a fluent interpretation of a human request is not proof that an agent has the person's real purpose. Ambiguous intentions, changing observations, missed windows, and irreversible actions should change how an agent transitions between states—not silently become higher confidence or authorization.

This is **software**, not a research paper or a model benchmark. It is deterministic and requires **no API key**, **no model**, and **no network**. It never executes an action: you connect its route to your own permission-checked executor.

## Quickstart

Python 3.11+; standard library only at runtime.

```bash
PYTHONPATH=src python -m purpose_gate examples/ambiguous_goal.json
PYTHONPATH=src python -m purpose_gate examples/shared_safe_action.json
PYTHONPATH=src python -m purpose_gate examples/observed_closure.json
PYTHONPATH=src python -m unittest discover -s tests -v
```

Or `pip install -e .` and then `python -m purpose_gate examples/ambiguous_goal.json`.

## Output example

For an ambiguous employment objective whose supporting purposes disagree on action fit:

```json
{
  "route": "PROBE",
  "reason_codes": ["PURPOSE_NOT_ESTABLISHED"],
  "next_probe": "Clarify the purpose and action fit with the human.",
  "input_sha256": "<sha256 of exact canonical input>",
  "remaining_seconds": 7200
}
```

`PROBE` is **a recommendation**, not an autonomous probing command. The application is responsible for getting fresh evidence, respecting cost/deadline budgets, acquiring appropriate human consent, and calling `decide()` again.

## Integration

```python
from purpose_gate import decide

next_transition = decide(runtime_snapshot)
if next_transition.route == 'PROCEED':
    # Executor must independently verify permissions and current state.
    pass
elif next_transition.route == 'PROBE':
    # Re-observe or seek clarification using authorized means.
    pass
elif next_transition.route == 'GATE':
    # Obtain explicit human review/approval.
    pass
else:
    # Do not dispatch this action.
    pass
```

The input schema is illustrated by the versioned examples. `intent.status` is **confirmed / ambiguous / unknown**; candidates state possible purposes and whether the proposed action supports them. This status means the *supplied evidence* is confirmed, **not that the unobservable true human objective is proven**. `permissions.allowed_tools` and `human_approved` must come from a trusted authority, never the same agent/model deciding to act. `world.closure` distinguishes `observed_closed` from `verified_terminal` and requires timestamp, TTL, and revision evidence.

A low-impact, reversible, whitelisted action may proceed if all supplied plausible purposes support it, even before a unique purpose is known. High-impact and irreversible actions require independently recorded human approval. Unknown/stale/contradictory state requests a bounded probe or review; urgency never generates permission.

## Deterministic routing priorities

1. Hard prohibition or unauthorized tool -> **STOP**.
2. Verified terminal window for an action requiring open access -> **STOP**.
3. Insufficient verified hard-deadline time, missing human approval, irreversible/high impact -> **GATE**.
4. Stale observation, state revision mismatch, evidence conflict, unconfirmed open route, unknown/ambiguous purpose -> **PROBE**, if time and evidence access allow, otherwise **GATE**.
5. Only authorized, fresh, purpose-aligned actions, or low-impact reversible actions shared by all plausible purposes -> **PROCEED**.

The controller is intentionally conservative. **It does not estimate purpose, create calibrated probabilities, assert success rates, settle real-world irreversibility, or infer legal permissions.** Inputs are evidence claims; establishing their integrity and provenance is the caller's responsibility.

## Where Jev can fit

Our earlier private Jev sensor uses TypeSafe's Jev model for four structured assessments: contract fit, preconditions, impact, evidence conflict. A Jev-based adapter could produce **advisory evidence** for this controller, but must not set `permissions`, `human_approved`, `verified_terminal`, or a goal-confirmed flag. Without an actual live model run, there are **no Jev calibration, cost, or latency claims** here.

## Why it is separate from Rubicon

[Rubicon](https://github.com/aamish-ahmad/rubicon) researches/evaluates commitment timing and partial observability. This library is an executable, product-shaped transition boundary. The two can connect later via versioned traces; neither implies the other's empirical evaluation is complete.

## Limits and safety

This is a local demonstration library, not a certified safety system. It assumes the input schema and trust boundary are enforced upstream. The route alone is insufficient authority to perform an external action. It does not discover all relevant goals or future world states. The input SHA-256 is for reproducible comparisons, **not tamper-proof provenance**. Scenarios are synthetic and contain no personal conversation traces. See [SECURITY.md](SECURITY.md).

MIT license. By Aamish Ahmad.

## Pure state transitions

In addition to snapshot routing, use `advance()` to distinguish an actual **new observation**, new **intent evidence**, or simple **time passage**. Transitions return an immutable decision record and a new snapshot without mutating the original. Authorization cannot be modified through these event types.

```python
from purpose_gate import advance

result = advance(previous_snapshot, {
    'type': 'world_observation',
    'at': '2026-10-23T20:01:00+05:30',
    'changes': {'revision': 5, 'observed_at': '2026-10-23T20:01:00+05:30'},
})
print(result.decision.route)  # PROBE when expected_revision is now outdated
```

This is a state transition, **not** an autonomous execution loop or a source-authentication mechanism. Store the full input/output trace only in a privacy-appropriate location.
