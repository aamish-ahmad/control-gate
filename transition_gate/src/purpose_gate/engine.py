"""Conservative, side-effect-free transition controller for human-directed agents.

This package does not infer latent human goals, grant permissions, or call tools.
Human intent and world state are input evidence, not established ground truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from typing import Any, Literal

Route = Literal['PROCEED', 'PROBE', 'GATE', 'STOP']
Alignment = Literal['supports', 'opposes', 'unknown']


@dataclass(frozen=True)
class Decision:
    route: Route
    reason_codes: tuple[str, ...]
    next_probe: str | None
    input_sha256: str
    remaining_seconds: int | None

    def as_dict(self) -> dict[str, Any]:
        return dict(route=self.route, reason_codes=list(self.reason_codes),
                    next_probe=self.next_probe, input_sha256=self.input_sha256,
                    remaining_seconds=self.remaining_seconds)


def _time(value: str, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f'{field} must be an ISO-8601 string')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{field} must be a valid ISO-8601 datetime') from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f'{field} must have a timezone')
    return dt


def _mapping(d: dict, key: str) -> dict:
    v = d.get(key)
    if not isinstance(v, dict):
        raise ValueError(f'{key} must be an object')
    return v


def _bool(obj: dict, key: str, default: bool = False) -> bool:
    value = obj.get(key, default)
    if not isinstance(value, bool):
        raise ValueError(f'{key} must be a boolean')
    return value


def _seconds(obj: dict, key: str, default: int = 0) -> int:
    value = obj.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f'{key} must be a nonnegative integer')
    return value


def decide(raw: dict[str, Any]) -> Decision:
    """Decide a safe *next route*; never execute or infer hidden intent.

    An agent cannot turn its estimate into permission: `permissions` and `world`
    should come from separately verified/trusted sources at the caller boundary.
    """
    if not isinstance(raw, dict):
        raise ValueError('input must be an object')
    now = _time(raw.get('now'), 'now')
    intent = _mapping(raw, 'intent')
    action = _mapping(raw, 'action')
    permissions = _mapping(raw, 'permissions')
    world = _mapping(raw, 'world')
    probe = _mapping(raw, 'probe')

    status = intent.get('status')
    if status not in ('confirmed', 'ambiguous', 'unknown'):
        raise ValueError('intent.status must be confirmed, ambiguous, or unknown')
    statement = intent.get('statement')
    if not isinstance(statement, str) or not statement.strip():
        raise ValueError('intent.statement must be a nonempty string')
    candidates = intent.get('candidates', [])
    if not isinstance(candidates, list) or any(not isinstance(c, dict) for c in candidates):
        raise ValueError('intent.candidates must be an array of objects')
    if len(candidates) > 64:
        raise ValueError('too many purpose candidates')
    for c in candidates:
        if not isinstance(c.get('purpose'), str) or not c['purpose'].strip():
            raise ValueError('candidate purpose must be a nonempty string')
        if c.get('action_alignment') not in ('supports', 'opposes', 'unknown'):
            raise ValueError('candidate action_alignment must be supports/opposes/unknown')
    if status == 'confirmed' and not candidates:
        raise ValueError('confirmed intent requires explicit purpose evidence')

    tool = action.get('tool')
    if not isinstance(tool, str) or not tool:
        raise ValueError('action.tool must be a nonempty string')
    impact = action.get('impact')
    if impact not in ('low', 'medium', 'high'):
        raise ValueError('action.impact must be low/medium/high')
    irreversible = _bool(action, 'irreversible')
    needs_open = _bool(action, 'requires_open_window')
    action_seconds = _seconds(action, 'estimated_seconds')
    expected_rev = action.get('expected_revision')
    world_rev = world.get('revision')
    if isinstance(expected_rev, bool) or not isinstance(expected_rev, int) or expected_rev < 0:
        raise ValueError('action.expected_revision must be a nonnegative integer')
    if isinstance(world_rev, bool) or not isinstance(world_rev, int) or world_rev < 0:
        raise ValueError('world.revision must be a nonnegative integer')

    allowed_tools = permissions.get('allowed_tools')
    if not isinstance(allowed_tools, list) or any(not isinstance(x, str) for x in allowed_tools):
        raise ValueError('permissions.allowed_tools must be an array of strings')
    prohibited = _bool(permissions, 'hard_prohibited')
    approval_required = _bool(permissions, 'approval_required')
    human_approved = _bool(permissions, 'human_approved')

    observed = _time(world.get('observed_at'), 'world.observed_at')
    max_age = _seconds(world, 'max_age_seconds')
    closure = world.get('closure')
    if closure not in ('open', 'observed_closed', 'verified_terminal', 'unknown'):
        raise ValueError('world.closure must be open/observed_closed/verified_terminal/unknown')
    deadline = _time(world['deadline'], 'world.deadline') if world.get('deadline') else None
    hard_deadline = _bool(world, 'deadline_verified_hard')
    has_conflict = _bool(world, 'material_evidence_conflict')
    probe_available = _bool(probe, 'available')
    probe_seconds = _seconds(probe, 'estimated_seconds')

    digest = hashlib.sha256(json.dumps(raw, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    remaining = int((deadline - now).total_seconds()) if deadline else None

    def out(route: Route, *reasons: str, next_probe: str | None = None) -> Decision:
        return Decision(route, tuple(reasons), next_probe, digest, remaining)

    def uncertainty(reason: str, question: str) -> Decision:
        # If information-gathering would exhaust a verified decision window,
        # do not silently convert urgency into permission to commit.
        sufficient_window = (remaining is None or not hard_deadline or
                             probe_seconds + action_seconds < remaining)
        if probe_available and sufficient_window:
            return out('PROBE', reason, next_probe=question)
        return out('GATE', reason, 'PROBE_UNAVAILABLE_OR_TOO_LATE', next_probe=question)

    # Authority is never derived from inferred purpose or model probabilities.
    if prohibited:
        return out('STOP', 'HARD_PROHIBITION')
    if tool not in allowed_tools:
        return out('STOP', 'TOOL_NOT_AUTHORIZED')
    if needs_open and closure == 'verified_terminal':
        return out('STOP', 'VERIFIED_TERMINAL_WINDOW')
    if deadline and hard_deadline and action_seconds >= remaining:
        return out('GATE', 'INSUFFICIENT_VERIFIED_TIME_TO_EXECUTE')
    if approval_required and not human_approved:
        return out('GATE', 'EXPLICIT_APPROVAL_REQUIRED')
    if (impact == 'high' or irreversible) and not human_approved:
        return out('GATE', 'CONSEQUENTIAL_COMMITMENT_REQUIRES_APPROVAL')

    if expected_rev != world_rev:
        return uncertainty('STATE_REVISION_CHANGED', 'Re-observe the current state and re-evaluate.')
    if observed > now:
        return uncertainty('OBSERVATION_FROM_FUTURE', 'Verify the source clock and observation.')
    if (now - observed).total_seconds() > max_age:
        return uncertainty('STATE_STALE', 'Refresh authoritative world state.')
    if has_conflict:
        return uncertainty('EVIDENCE_CONFLICT', 'Resolve material evidence conflict.')
    if needs_open and closure != 'open':
        return uncertainty('WINDOW_NOT_CONFIRMED_OPEN', 'Check the authorized current route and governing policy.')

    alignments = {c['action_alignment'] for c in candidates}
    if not candidates or 'opposes' in alignments or 'unknown' in alignments:
        return uncertainty('PURPOSE_NOT_ESTABLISHED', 'Clarify the purpose and action fit with the human.')
    if status != 'confirmed':
        if irreversible or impact != 'low':
            return uncertainty('AMBIGUOUS_PURPOSE_CONSEQUENTIAL_ACTION', 'Confirm the dominant purpose with the human.')
        # Safe common action across supplied purposes is possible without
        # pretending their hidden ranking has been identified.
        return out('PROCEED', 'LOW_IMPACT_REVERSIBLE_ACTION_SHARED_ACROSS_PURPOSES')
    return out('PROCEED', 'AUTHORIZED_FRESH_PURPOSE_ALIGNED_ACTION')
