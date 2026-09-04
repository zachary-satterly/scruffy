#!/usr/bin/env python3
"""Shared legacy/current rendering behavior and safe dashboard evidence."""
import base64
import json
import unittest
import tempfile
from pathlib import Path

from report_contract import capability_rows, score_number, score_order, score_rows, plain_category_label
from render_dashboard import render as dashboard, embed_asset
from render_markdown import render as markdown
from render_onepager import score_order as pager_order

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / 'evals' / 'continuity'


class ReportNormalization(unittest.TestCase):
    def setUp(self):
        self.registry = json.loads((FIXTURE / 'revision.json').read_text())
        self.context = json.loads((FIXTURE / 'context.json').read_text())
        self.decisions = json.loads((FIXTURE / 'decisions.json').read_text())

    def test_current_and_legacy_surfaces_share_capability_labels_and_score_order(self):
        self.context['capabilities'] = [
            {'capability': 'Legacy browser check', 'status': 'available', 'scope': 'Recorded <coverage> & notes'},
            {'key': 'source_read', 'status': 'unavailable', 'scope': 'No source supplied'},
        ]
        self.context['scores'] = [
            {'category': 'visual', 'score': '0 · clear', 'evidence': 'zero evidence'},
            {'category': 'performance', 'score': 'N/A', 'evidence': 'unscored evidence'},
            {'category': 'interaction', 'score': 3, 'evidence': 'three evidence'},
            {'category': 'Legacy category prose', 'score': '2 · material', 'evidence': 'two evidence'},
        ]
        doc = dashboard(self.registry, self.context, self.decisions, FIXTURE / 'context.json')
        md = markdown(self.registry, self.context, self.decisions)
        score_section = doc.split('<section id="score">', 1)[1].split('</section>', 1)[0]
        for rendered in (score_section, md.split('## Quality scores and result', 1)[1]):
            self.assertLess(rendered.index('three evidence'), rendered.index('two evidence'))
            self.assertLess(rendered.index('two evidence'), rendered.index('zero evidence'))
            self.assertLess(rendered.index('zero evidence'), rendered.index('unscored evidence'))
        self.assertIn('Legacy browser check', doc)
        self.assertIn('Legacy browser check', md)
        self.assertIn('Recorded &lt;coverage&gt; &amp; notes', doc)
        self.assertIn('Legacy category prose', doc)
        self.assertIn('Interaction and feedback · 3 of 3', doc)
        self.assertIs(pager_order, score_order)
        # Entirely legacy scores still drive the summary strip.
        self.context['scores'][2]['score'] = '3 — major'
        doc = dashboard(self.registry, self.context, self.decisions, FIXTURE / 'context.json')
        self.assertIn('Interaction and feedback · 3 of 3', doc)

    def test_unscored_invalid_and_unknown_values_are_not_invented_scores(self):
        for value in (True, False, -1, 4, '30 points', 'unscored', None, {}, []):
            self.assertIsNone(score_number(value))
        for value in (0, '0', '0 · clear', '0 — clear', '0 - clear'):
            self.assertEqual(score_number(value), 0)
        self.assertEqual(capability_rows({'capabilities': [{'capability': 'Owner supplied label'}]})[0][0], 'Owner supplied label')
        self.assertEqual(plain_category_label("information-architecture"), "Navigation and organization")
        self.assertEqual(plain_category_label("implementation-shape"), "Reliability and maintainability")
        self.assertEqual(plain_category_label("Owner supplied prose"), "Owner supplied prose")

    def test_shared_projection_keeps_humanization(self):
        options = {'item_labels': {'AS-01': 'Finding 1'}, 'evidence_assets': {}}
        self.assertEqual(score_rows({'scores': [{'category': 'copy', 'score': 2, 'evidence': 'AS-01 has UI copy'}]}, **options)[0][2], 'Finding 1 has interface copy')
        self.assertEqual(capability_rows({'capabilities': [{'key': 'source_read', 'scope': 'AS-01 has UI copy'}]}, **options)[0][2], 'Finding 1 has interface copy')


class DashboardEvidence(unittest.TestCase):
    def test_only_confined_raster_evidence_is_embedded(self):
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl6pN8AAAAASUVORK5CYII=')
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            bundle = root / 'bundle'; bundle.mkdir()
            (bundle / 'valid.png').write_bytes(png)
            self.assertEqual(embed_asset('valid.png', bundle), 'data:image/png;base64,' + base64.b64encode(png).decode())
            (root / 'outside.png').write_bytes(png)
            (bundle / 'escape.png').symlink_to(root / 'outside.png')
            (bundle / 'text.png').write_text('private nonimage text')
            (bundle / 'unsupported.txt').write_bytes(png)
            (bundle / 'mismatch.jpg').write_bytes(png)
            (bundle / 'vector.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
            for name in ('../outside.png', str(root / 'outside.png'), str(bundle / 'valid.png'), 'escape.png', 'text.png', 'unsupported.txt', 'mismatch.jpg', 'vector.svg', 'missing.png'):
                with self.subTest(name=name):
                    self.assertEqual(embed_asset(name, bundle), '')
            from evidence_assets import MAX_RASTER_BYTES
            with (bundle / 'huge.png').open('wb') as handle:
                handle.write(png)
                handle.truncate(MAX_RASTER_BYTES + 1)
            self.assertEqual(embed_asset('huge.png', bundle), '')


if __name__ == '__main__':
    unittest.main()
