import copy
import json
import pathlib
import unittest
from datetime import datetime, timedelta, timezone
from purpose_gate import decide

EX = pathlib.Path(__file__).resolve().parents[1] / 'examples'


def load(name='confirmed_safe_action.json'):
    return json.loads((EX / name).read_text(encoding='utf-8'))


class TransitionTests(unittest.TestCase):
    def test_confirmed_reversible_proceeds(self):
        self.assertEqual(decide(load()).route, 'PROCEED')

    def test_ambiguous_divergent_purpose_probes(self):
        self.assertEqual(decide(load('ambiguous_goal.json')).route, 'PROBE')

    def test_shared_low_impact_action_proceeds(self):
        d = decide(load('shared_safe_action.json'))
        self.assertEqual(d.route, 'PROCEED')
        self.assertIn('LOW_IMPACT_REVERSIBLE_ACTION_SHARED_ACROSS_PURPOSES', d.reason_codes)

    def test_observed_closure_not_mistaken_for_terminal(self):
        self.assertEqual(decide(load('observed_closure.json')).route, 'PROBE')

    def test_verified_terminal_stops_action(self):
        x = load('observed_closure.json')
        x['world']['closure'] = 'verified_terminal'
        self.assertEqual(decide(x).route, 'STOP')

    def test_unknown_closure_probes_for_open_dependent_action(self):
        x = load('observed_closure.json')
        x['world']['closure'] = 'unknown'
        self.assertEqual(decide(x).route, 'PROBE')

    def test_hard_prohibition_overrides_everything(self):
        x = load()
        x['permissions']['hard_prohibited'] = True
        x['permissions']['human_approved'] = True
        self.assertEqual(decide(x).route, 'STOP')

    def test_tool_not_whitelisted_stops(self):
        x = load()
        x['permissions']['allowed_tools'] = []
        self.assertEqual(decide(x).route, 'STOP')

    def test_approval_requirement_gates(self):
        x = load()
        x['permissions']['approval_required'] = True
        self.assertEqual(decide(x).route, 'GATE')

    def test_approved_action_no_longer_gated_by_approval_only(self):
        x = load()
        x['permissions'].update(approval_required=True, human_approved=True)
        self.assertEqual(decide(x).route, 'PROCEED')

    def test_irreversible_requires_approval(self):
        x = load()
        x['action']['irreversible'] = True
        self.assertEqual(decide(x).route, 'GATE')

    def test_high_impact_requires_approval(self):
        x = load()
        x['action']['impact'] = 'high'
        self.assertEqual(decide(x).route, 'GATE')

    def test_stale_state_requires_recheck(self):
        x = load()
        x['world']['max_age_seconds'] = 5
        self.assertEqual(decide(x).route, 'PROBE')

    def test_state_revision_requires_recheck(self):
        x = load()
        x['action']['expected_revision'] = 1
        self.assertEqual(decide(x).route, 'PROBE')

    def test_material_conflict_requires_recheck(self):
        x = load()
        x['world']['material_evidence_conflict'] = True
        self.assertEqual(decide(x).route, 'PROBE')

    def test_probe_unavailable_gates(self):
        x = load('ambiguous_goal.json')
        x['probe']['available'] = False
        self.assertEqual(decide(x).route, 'GATE')

    def test_probe_cost_crosses_deadline_gates(self):
        x = load('ambiguous_goal.json')
        x['world']['deadline'] = '2026-10-23T20:02:00+05:30'
        x['probe']['estimated_seconds'] = 180
        self.assertEqual(decide(x).route, 'GATE')

    def test_hard_deadline_not_assumed_without_verification(self):
        x = load('ambiguous_goal.json')
        x['world']['deadline'] = '2026-10-23T20:01:00+05:30'
        x['world']['deadline_verified_hard'] = False
        self.assertEqual(decide(x).route, 'PROBE')

    def test_insufficient_hard_time_requires_human_gate(self):
        x = load()
        x['world'].update(deadline='2026-10-23T20:00:05+05:30', deadline_verified_hard=True)
        x['action']['estimated_seconds'] = 10
        self.assertEqual(decide(x).route, 'GATE')

    def test_mixed_purpose_conflict_probes(self):
        x = load('shared_safe_action.json')
        x['intent']['candidates'][1]['action_alignment'] = 'opposes'
        self.assertEqual(decide(x).route, 'PROBE')

    def test_ambiguous_medium_impact_action_probes_even_if_shared(self):
        x = load('shared_safe_action.json')
        x['action']['impact'] = 'medium'
        self.assertEqual(decide(x).route, 'PROBE')

    def test_unknown_purpose_probes(self):
        x = load()
        x['intent']['status'] = 'unknown'
        x['intent']['candidates'] = []
        self.assertEqual(decide(x).route, 'PROBE')

    def test_missing_timezone_rejected(self):
        x = load()
        x['now'] = '2026-10-23T20:00:00'
        with self.assertRaisesRegex(ValueError, 'timezone'):
            decide(x)

    def test_untrusted_boolean_shape_rejected(self):
        x = load()
        x['permissions']['human_approved'] = 'true'
        with self.assertRaisesRegex(ValueError, 'boolean'):
            decide(x)

    def test_invalid_revision_rejected(self):
        x = load()
        x['world']['revision'] = -1
        with self.assertRaisesRegex(ValueError, 'nonnegative integer'):
            decide(x)

    def test_deterministic_digest_and_output(self):
        x = load()
        a, b = decide(x), decide(copy.deepcopy(x))
        self.assertEqual(a, b)
        self.assertEqual(len(a.input_sha256), 64)

    def test_observation_in_future_never_silent_proceed(self):
        x = load()
        x['world']['observed_at'] = '2026-10-23T20:01:00+05:30'
        self.assertEqual(decide(x).route, 'PROBE')


if __name__ == '__main__':
    unittest.main()
