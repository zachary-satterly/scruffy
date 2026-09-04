#!/usr/bin/env python3
"""Historical repair achievements stay bound to the audit and verified packet."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from outcomes import summarize

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    registry = json.loads((ROOT / 'evals/continuity/revision.json').read_text())
    item = registry['items'][0]
    item['depends_on'] = []
    item['principle_refs'] = ['P-test']
    item['fix_packet'] = {
        'target': [{'kind': 'file', 'value': 'index.html'}],
        'change': 'Apply the approved repair', 'effort': 'S', 'rollback': 'Revert repair',
        'acceptance': [{'kind': 'command', 'run': 'true', 'summary': 'Acceptance succeeds'}],
    }
    registry['items'] = [item]
    registry['presentation'] = {'prioritized_finding_ids': [item['id']], 'prioritized_enhancement_ids': [], 'strength_ids': [], 'cleared_ids': []}
    decisions = json.loads((ROOT / 'evals/continuity/decisions.json').read_text())
    decisions['decisions'] = [decisions['decisions'][0]]
    decisions['decisions'][0]['decision'] = 'approve'
    verification = {
        'schema_version': '1.0', 'audit_id': registry['audit_id'], 'revision_id': registry['revision_id'],
        'executed_commands': True,
        'items': [{'id': item['id'], 'decision': 'approve', 'result': 'verified',
                   'checks': [{'index': 0, 'kind': 'command', 'result': 'pass'}]}],
    }
    return registry, decisions, verification


def next_registry(registry, status='fixed', suffix='next'):
    result = copy.deepcopy(registry)
    result['baseline_revision_id'] = registry['revision_id']
    result['revision_id'] += '-' + suffix
    result['items'][0]['status'] = status
    result['items'][0]['revision_disposition'] = 'reopened' if status == 'open' else status
    result['presentation']['prioritized_finding_ids'] = [result['items'][0]['id']] if status == 'open' else []
    result['presentation']['cleared_ids'] = [] if status == 'open' else [result['items'][0]['id']]
    return result


class Outcomes(unittest.TestCase):
    def test_verified_approval_survives_fixed_then_reopened_and_refixed(self):
        registry, _, _ = fixture()
        fixed = next_registry(registry)
        reopened = next_registry(fixed, 'open', 'reopen')
        refixed = next_registry(reopened)
        first = (registry, {'AS-01': 'approve'}, {'AS-01': 'verified'})
        report = summarize([first, (fixed, {}, {})])
        for key in ('raised', 'approved', 'verified', 'fixed'):
            self.assertEqual(report['total'][key], 1)
        self.assertEqual(report['total']['verify_rate'], 1.0)
        self.assertEqual(report['rules']['P-test'], {'raised': 1, 'approved': 1, 'rejected': 0})
        report = summarize([first, (fixed, {}, {}), (reopened, {}, {}), (refixed, {}, {})])
        self.assertEqual(report['total']['reopened'], 1)
        self.assertEqual(report['total']['resolved'], 1)
        self.assertEqual(report['total']['reopen_rate'], 1.0)
        self.assertEqual(report['total']['verified'], 1)

    def test_unproven_or_cleared_results_never_become_verified(self):
        registry, _, _ = fixture()
        for verdict in ('failed', 'manual', 'not_run', ''):
            with self.subTest(verdict=verdict):
                report = summarize([(registry, {'AS-01': 'approve'}, {'AS-01': verdict}), (next_registry(registry, 'cleared'), {}, {})])
                self.assertEqual(report['total']['verified'], 0)
        report = summarize([(registry, {'AS-01': 'pending'}, {'AS-01': 'verified'})])
        self.assertEqual(report['total']['verified'], 0)

    def test_identical_ids_in_different_audits_are_distinct(self):
        registry, _, _ = fixture()
        second = copy.deepcopy(registry)
        second['audit_id'] = 'another-audit'
        second['target'] = 'another-target'
        report = summarize([(registry, {'AS-01': 'approve'}, {}), (second, {}, {})])
        self.assertEqual(report['total']['raised'], 2)
        self.assertEqual(report['total']['approved'], 1)
        self.assertEqual(len(report['items']), 2)
        with self.assertRaisesRegex(ValueError, 'duplicate audit/revision'):
            summarize([(registry, {}, {}), (registry, {}, {})])
        changed = next_registry(registry)
        changed['items'][0]['identity_key'] = 'different-identity'
        with self.assertRaisesRegex(ValueError, 'reused an item identity'):
            summarize([(registry, {}, {}), (changed, {}, {})])

    def test_oldest_first_and_explicit_rejections_are_required(self):
        registry, _, _ = fixture()
        fixed = next_registry(registry)
        with self.assertRaisesRegex(ValueError, 'oldest first'):
            summarize([(fixed, {}, {}), (registry, {}, {})])
        histories = []
        for index in range(3):
            other = copy.deepcopy(registry)
            other['audit_id'] = f'audit-{index}'
            histories.append((other, {'AS-01': 'pending'}, {}))
        self.assertEqual(summarize(histories)['retirement_candidates'], [])
        deferred = [(reg, {'AS-01': 'defer'}, {}) for reg, _, _ in histories]
        self.assertEqual(summarize(deferred)['retirement_candidates'], [])
        rejected = [(reg, {'AS-01': 'reject'}, {}) for reg, _, _ in histories]
        self.assertEqual(summarize(rejected)['retirement_candidates'], ['P-test'])
        rejected[-1] = (rejected[-1][0], {'AS-01': 'approve'}, {})
        self.assertEqual(summarize(rejected)['retirement_candidates'], [])

    def test_cli_binds_decisions_and_actual_receipt_and_preserves_output_on_failure(self):
        registry, decisions, verification = fixture()
        with tempfile.TemporaryDirectory() as raw:
            base = Path(raw)
            paths = [base / name for name in ('findings.json', 'decisions.json', 'verification.json')]
            output = base / 'outcomes.json'
            def run(reg=registry, dec=decisions, ver=verification, out=output):
                for path, document in zip(paths, (reg, dec, ver)):
                    path.write_text(json.dumps(document))
                return subprocess.run([sys.executable, str(ROOT / 'scripts/outcomes.py'), ':'.join(map(str, paths)), '--output', str(out)], capture_output=True, text=True)
            self.assertEqual(run().returncode, 0)
            original = output.read_bytes()
            self.assertEqual(json.loads(original)['total']['verified'], 1)
            for key, value in (('audit_id', 'different'), ('revision_id', 'different')):
                wrong = copy.deepcopy(verification)
                wrong[key] = value
                self.assertNotEqual(run(ver=wrong).returncode, 0)
                self.assertEqual(output.read_bytes(), original)
            for mutate in (
                lambda v: v['items'].append(copy.deepcopy(v['items'][0])),
                lambda v: v['items'][0].update(id='AS-99'),
                lambda v: v['items'][0].update(checks=[]),
                lambda v: v['items'][0]['checks'][0].update(result='not_run'),
                lambda v: v.update(executed_commands=False),
            ):
                wrong = copy.deepcopy(verification); mutate(wrong)
                self.assertNotEqual(run(ver=wrong).returncode, 0)
                self.assertEqual(output.read_bytes(), original)
            wrong_decisions = copy.deepcopy(decisions)
            wrong_decisions['audit_id'] = 'different'
            self.assertNotEqual(run(dec=wrong_decisions).returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            self.assertNotEqual(run(out=paths[0]).returncode, 0)
            self.assertEqual(json.loads(paths[0].read_text()), registry)


if __name__ == '__main__':
    unittest.main()
