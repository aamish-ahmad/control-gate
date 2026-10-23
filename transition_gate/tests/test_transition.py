import json
import pathlib
import unittest
from purpose_gate import advance, decide

P = pathlib.Path(__file__).resolve().parents[1] / 'examples'


def sample(name='confirmed_safe_action.json'):
    return json.loads((P / name).read_text(encoding='utf-8'))


class TemporalTransitionTests(unittest.TestCase):
    def test_tick_causes_stale_snapshot(self):
        before = sample()
        a = advance(before, {'type':'tick', 'at':'2026-10-23T21:00:00+05:30'})
        self.assertEqual(a.decision.route, 'PROBE')
        self.assertEqual(decide(before).route, 'PROCEED')

    def test_world_observation_updates_revision(self):
        before = sample()
        a = advance(before, {'type':'world_observation', 'at':'2026-10-23T20:01:00+05:30',
            'changes':{'revision':3,'observed_at':'2026-10-23T20:01:00+05:30'}})
        self.assertEqual(a.decision.route, 'PROBE')
        self.assertEqual(a.state['world']['revision'], 3)
        self.assertEqual(before['world']['revision'], 2)

    def test_observed_closed_is_not_terminal(self):
        before = sample('observed_closure.json')
        a = advance(before, {'type':'world_observation', 'at':'2026-10-23T20:01:00+05:30',
            'changes':{'closure':'observed_closed','observed_at':'2026-10-23T20:01:00+05:30'}})
        self.assertEqual(a.decision.route, 'PROBE')

    def test_new_intent_evidence_can_disambiguate(self):
        before = sample('ambiguous_goal.json')
        a = advance(before, {'type':'intent_evidence','at':'2026-10-23T20:01:00+05:30',
            'changes':{'status':'confirmed','candidates':[{'purpose':'financial continuity','action_alignment':'supports'}]}})
        self.assertEqual(a.decision.route, 'PROCEED')
        self.assertEqual(decide(before).route, 'PROBE')

    def test_event_cannot_grant_permission(self):
        before = sample()
        for k in ['permissions','human_approved','authorizedScope']:
            with self.subTest(k=k):
                with self.assertRaises(ValueError):
                    advance(before, {'type':'world_observation', 'at':'2026-10-23T20:01:00+05:30',
                                     'changes':{k:True}})

    def test_event_cannot_go_back_in_time(self):
        with self.assertRaises(ValueError):
            advance(sample(), {'type':'tick','at':'2026-10-23T19:58:00+05:30'})

    def test_unknown_event_type_rejected(self):
        with self.assertRaises(ValueError):
            advance(sample(), {'type':'authorization_change','at':'2026-10-23T20:01:00+05:30',
                               'changes':{'human_approved':True}})

    def test_transition_has_stable_sha(self):
        before = sample()
        event = {'type':'tick', 'at':'2026-10-23T20:01:00+05:30'}
        self.assertEqual(advance(before, event).previous_sha256,
                         advance(before, event).previous_sha256)


if __name__ == '__main__':
    unittest.main()
