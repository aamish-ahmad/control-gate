"""Pure, appendable state transitions; never mutate caller input or execute tools.

Only event types that cannot grant authority are accepted. Authorization changes
must be ingested through an independently trusted application boundary.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from .engine import Decision, _time, decide

_ALLOWED_WORLD = frozenset({'revision', 'observed_at', 'closure', 'deadline',
                            'deadline_verified_hard', 'max_age_seconds',
                            'material_evidence_conflict'})
_ALLOWED_INTENT = frozenset({'statement', 'status', 'candidates'})


@dataclass(frozen=True)
class Transition:
    state: dict[str, Any]
    decision: Decision
    event_type: str
    previous_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return {'state': self.state, 'decision': self.decision.as_dict(),
                'event_type': self.event_type, 'previous_sha256': self.previous_sha256}


def advance(previous: dict[str, Any], event: dict[str, Any]) -> Transition:
    """Transition with new observations or intent evidence, then route action.

    Schema: {"type":"world_observation"|"intent_evidence"|"tick",
             "at":"ISO8601 with timezone", "changes": {...}}

    No permission/approval/authorization mutation event is accepted. A supplied
    world fact is still only a claim until its caller verifies the source.
    """
    if not isinstance(previous, dict) or not isinstance(event, dict):
        raise ValueError('previous and event must be objects')
    prior_time = _time(previous.get('now'), 'previous.now')
    at = _time(event.get('at'), 'event.at')
    if at < prior_time:
        raise ValueError('event time cannot precede previous state time')
    kind = event.get('type')
    changes = event.get('changes', {})
    if not isinstance(changes, dict):
        raise ValueError('event.changes must be an object')
    if kind == 'world_observation':
        if not changes or not set(changes) <= _ALLOWED_WORLD:
            raise ValueError('world_observation permits only world evidence fields')
    elif kind == 'intent_evidence':
        if not changes or not set(changes) <= _ALLOWED_INTENT:
            raise ValueError('intent_evidence permits only declared intent fields')
    elif kind == 'tick':
        if changes:
            raise ValueError('tick cannot change fields')
    else:
        raise ValueError('unknown event type')

    snapshot = deepcopy(previous)
    snapshot['now'] = event['at']
    if kind != 'tick':
        key = 'world' if kind == 'world_observation' else 'intent'
        if not isinstance(snapshot.get(key), dict):
            raise ValueError(f'previous.{key} must be an object')
        snapshot[key].update(deepcopy(changes))

    result = decide(snapshot)
    previous_hash = hashlib.sha256(json.dumps(previous, sort_keys=True,
             separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
    return Transition(snapshot, result, kind, previous_hash)
