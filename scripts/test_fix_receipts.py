#!/usr/bin/env python3
"""A completed repair must account for every promised check in its own revision."""
import copy
import json
import unittest
from pathlib import Path

from validate_audit import validate_fix_verification

FIXTURE = Path(__file__).resolve().parents[1] / 'evals/durability'


class FixReceipts(unittest.TestCase):
    def test_receipt_binding_and_check_coverage(self):
        baseline = json.loads((FIXTURE / 'baseline.json').read_text())
        current = json.loads((FIXTURE / 'revision-valid-fixed-with-verification.json').read_text())
        receipt = json.loads((FIXTURE / 'verification-fixed.json').read_text())
        receipt['revision_id'] = baseline['revision_id']
        validate_fix_verification(current, baseline, receipt)
        mutations = []
        for field in ('audit_id', 'revision_id'):
            bad = copy.deepcopy(receipt)
            bad[field] = 'unrelated'
            mutations.append((field, current, bad))
        for checks in ([{'kind': 'manual', 'result': 'manual', 'index': 0}], ['pass'], [], receipt['items'][0]['checks'][:1]):
            bad = copy.deepcopy(receipt)
            bad['items'][0]['checks'] = checks
            mutations.append(('incomplete or malformed checks', current, bad))
        for key, value in (('kind', 'manual'), ('index', 1), ('result', 'fail')):
            bad = copy.deepcopy(receipt)
            bad['items'][0]['checks'][0][key] = value
            mutations.append((key, current, bad))
        for key, value in (('decision', 'reject'), ('result', 'failed')):
            bad = copy.deepcopy(receipt)
            bad['items'][0][key] = value
            mutations.append((key, current, bad))
        bad = copy.deepcopy(receipt)
        bad['items'].append(copy.deepcopy(bad['items'][0]))
        mutations.append(('duplicate row', current, bad))
        for field, value in (('verification_override', 'Trust me'), ('evidence_refs', ['specialist_review_fake'])):
            bad_current = copy.deepcopy(current)
            next(i for i in bad_current['items'] if i['id'] == 'AS-01')[field] = value
            bad_receipt = copy.deepcopy(receipt)
            bad_receipt['items'][0]['checks'][0]['result'] = 'fail'
            mutations.append(('untyped bypass', bad_current, bad_receipt))
        for label, source, evidence in mutations:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    validate_fix_verification(source, baseline, evidence)


if __name__ == '__main__':
    unittest.main()
