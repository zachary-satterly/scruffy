#!/usr/bin/env python3
"""Reject invalid acceptance inputs before any command or receipt write."""
import copy
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class VerifierInputs(unittest.TestCase):
    def test_preflight_and_valid_neighbor(self):
        registry = json.loads((ROOT / 'evals/continuity/revision.json').read_text())
        decisions = json.loads((ROOT / 'evals/continuity/decisions.json').read_text())
        with tempfile.TemporaryDirectory() as raw:
            directory = Path(raw)
            marker = directory / 'executed'
            command = shlex.join([sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()'])
            item = next(i for i in registry['items'] if i['id'] == 'AS-02')
            item['fix_packet'] = {
                'target': [{'kind': 'file', 'value': 'index.html'}],
                'change': 'Restore addressable navigation.', 'effort': 'S',
                'rollback': 'Revert the navigation change.',
                'acceptance': [{'kind': 'command', 'run': command}],
            }
            next(r for r in decisions['decisions'] if r['item_id'] == item['id'])['decision'] = 'approve'
            cases = []
            for field in ('audit_id', 'revision_id', 'baseline_revision_id'):
                bad = copy.deepcopy(decisions)
                bad[field] = 'unrelated'
                cases.append((field, registry, bad, []))
            duplicate = copy.deepcopy(decisions)
            duplicate['decisions'].append(copy.deepcopy(duplicate['decisions'][0]))
            cases.append(('duplicate decision', registry, duplicate, []))
            for patch in ({'run': ''}, {'kind': 'unknown'}, {'timeout': 0}, {'timeout': True}, {'expect': {'exit_code': 'zero'}}, {'expect': {'stdout_contains': 123}}):
                bad = copy.deepcopy(registry)
                next(i for i in bad['items'] if i['id'] == 'AS-02')['fix_packet']['acceptance'][0].update(patch)
                cases.append((str(patch), bad, decisions, []))
            cases.append(('pending execution', registry, decisions, ['--include-pending']))
            registry_path, decisions_path, output = [directory / n for n in ('findings.json', 'decisions.json', 'verification.json')]
            for label, source, approvals, extra in cases:
                with self.subTest(label=label):
                    marker.unlink(missing_ok=True)
                    registry_path.write_text(json.dumps(source))
                    decisions_path.write_text(json.dumps(approvals))
                    output.write_text('existing receipt')
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_fixes.py'), str(registry_path), '--decisions', str(decisions_path), '--execute', '--output', str(output), *extra], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0, result.stdout)
                    self.assertFalse(marker.exists(), label)
                    self.assertEqual(output.read_text(), 'existing receipt')
                    self.assertNotIn('Traceback', result.stderr)
            registry_path.write_text(json.dumps(registry))
            decisions_path.write_text(json.dumps(decisions))
            for destination in (directory / 'missing/verification.json', directory, registry_path, decisions_path):
                with self.subTest(destination=str(destination)):
                    result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_fixes.py'), str(registry_path), '--decisions', str(decisions_path), '--execute', '--output', str(destination)], capture_output=True, text=True)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(marker.exists())
                    self.assertEqual(json.loads(registry_path.read_text()), registry)
                    self.assertEqual(json.loads(decisions_path.read_text()), decisions)
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_fixes.py'), str(registry_path), '--decisions', str(decisions_path), '--execute', '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            self.assertEqual(json.loads(output.read_text())['items'][0]['result'], 'verified')


if __name__ == '__main__':
    unittest.main()
