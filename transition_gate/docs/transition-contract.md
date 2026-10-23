# Transition contract v0.1

This note defines a **side-effect-free** next-action router. It does not model all human objectives, does not estimate true intent, and does not replace human authorization.

## Inputs

- `now`: offset-aware ISO timestamp.
- `intent.statement`, `intent.status`: natural-language human abstraction and supplied certainty about that statement (`confirmed`, `ambiguous`, `unknown`).
- `intent.candidates`: possible meanings/purposes. `action_alignment` is `supports`, `opposes`, `unknown` for the proposed action; these are *evidence claims*, not calibrated probabilities.
- `action`: intended tool, impact, irreversibility, open-window dependency, estimated runtime, expected state revision.
- `permissions`: trusted allowlist and hard prohibition, explicit approval requirement and independently obtained human approval.
- `world`: observed state revision/timestamp/TTL, closure (`open`, `observed_closed`, `verified_terminal`, `unknown`), optionally deadline and verification status, contradiction flag.
- `probe`: existence and expected duration of a permissible evidence-gathering operation.

## Time and commitment

Time estimates are not probabilities. If an uncertain purpose could be clarified within a verified hard window, the controller proposes a probe; if not, it gates to a human rather than upgrading its confidence. A verified terminal state stops a tool action that requires an open route. Observed closure alone is not finality.

## Human purpose uncertainty

The example abstraction *"I want a better job"* admits multiple possible purposes: income, moving locations, family independence, research opportunity, etc. The system does not infer hidden true purpose. If the proposed action conflicts with a plausible purpose, it probes. If all currently supplied purposes support a **low-impact reversible** read, it may proceed even before purpose is unique.

## Model adapter

An optional model such as Jev can suggest `action_alignment` or highlight evidence conflict. Its numbers must not become implicit authorization, goal confirmation, closure verification, or a claim of calibrated expected utility. Future work must freeze a labeled dataset, preserve time-scoped evidence, compare simple baselines, and measure unsafe PROCEED rate and calibration before advertising model value.

## Thread-safety and deployment

The controller checks a version in the snapshot, but this is NOT a transaction lock. The executor must recheck against live authoritative state and policy at execution; use idempotency, transaction locks/compare-and-swap where relevant. No current package code calls network or alters external systems.

## `advance(previous, event)`

`event.type` is `world_observation` (new world evidence), `intent_evidence` (changed interpretation/clarification), or `tick` (time passed). `event.at` cannot precede the previous `now`. Unknown event keys/types fail validation; permission changes cannot be injected through model evidence. The return carries a new state, routing decision, and SHA-256 digest of the preceding state. An adapter should preserve source signatures/links outside this library if strong provenance is required.
