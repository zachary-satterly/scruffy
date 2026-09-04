#!/usr/bin/env python3
"""Exercise destructive-input boundaries and honest draft/scan lifecycle."""
import contextlib
import copy
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scaffold_audit
import scan

ROOT = Path(__file__).resolve().parents[1]

class LifecycleInputs(unittest.TestCase):
    def test_scaffold_preserves_existing_and_invalid_destination(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            output = root / 'existing'
            output.mkdir()
            sentinel = output / 'findings.json'
            sentinel.write_text('preserve me')
            for destination, audit_id in [(output, 'demo'), (root/'invalid', ' ')]:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    scaffold_audit.main(['--audit-id',audit_id,'--title','Demo','--target','Demo','--out',str(destination)])
            self.assertEqual(sentinel.read_text(),'preserve me')
            self.assertFalse((root/'invalid').exists())

    def test_scaffold_validation_failure_publishes_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            dest = Path(raw) / 'draft'
            with patch.object(scaffold_audit.subprocess,'run', return_value=subprocess.CompletedProcess([],1,'invalid','')), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(scaffold_audit.main(['--audit-id','demo','--title','Demo','--target','Demo','--out',str(dest)]),1)
            self.assertFalse(dest.exists())
            self.assertEqual(list(Path(raw).iterdir()),[])

    def test_scaffold_does_not_invent_observations(self):
        _, context, _ = scaffold_audit.build('demo','Demo','Demo','DM','audit','not_authorized',[])
        self.assertTrue(all(r['score']=='N/A' for r in context['scores']))
        self.assertTrue(all(r['status']=='not_run' for r in context['tasks']))
        self.assertTrue(all(r['verification']=='not_verified' for r in context['evidence_assets']))

    def test_scan_tempfile_cleanup_even_on_failure(self):
        for fail in [False,True]:
            response = io.BytesIO(b'<html>demo</html>')
            with patch.object(scan.urllib.request,'urlopen',return_value=response):
                try:
                    with scan.acquire('https://example.invalid') as (path, origin):
                        self.assertTrue(path.is_file())
                        if fail: raise ValueError('downstream failure')
                except ValueError: pass
            self.assertFalse(path.exists())

    def test_scan_limits_and_preserves_local_source(self):
        with patch.object(scan,'MAX_HTML_BYTES',8), patch.object(scan.urllib.request,'urlopen',return_value=io.BytesIO(b'x'*9)):
            with self.assertRaises(ValueError), scan.acquire('https://example.invalid'): pass
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'input.html';path.write_text('<html>hello</html>')
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                scan.main([str(path),'--output',str(path)])
            self.assertEqual(path.read_text(),'<html>hello</html>')

    def test_migration_rejects_foreign_duplicate_and_unbound_proof(self):
        registry=json.loads((ROOT/'evals/continuity/revision.json').read_text())
        decisions=json.loads((ROOT/'evals/continuity/decisions.json').read_text())
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw);rp=base/'registry.json';rp.write_text(json.dumps(registry))
            for mutation in ['foreign','duplicate','revision','proof']:
                prior=copy.deepcopy(decisions)
                if mutation=='foreign': prior['audit_id']='another-audit'
                if mutation=='duplicate': prior['decisions'].append(copy.deepcopy(prior['decisions'][0]))
                if mutation=='revision': prior['revision_id']='unrelated'
                dp=base/'decisions.json';dp.write_text(json.dumps(prior));output=base/'out.json'
                args=[sys.executable,str(ROOT/'scripts/migrate_decisions.py'),str(dp),str(rp),str(output)]
                if mutation=='proof':
                    proof=base/'proof.json';proof.write_text(json.dumps({'schema_version':'1.0','audit_id':'foreign','revision_id':registry['revision_id'],'items':[]}));args+=['--verification',str(proof)]
                result=subprocess.run(args,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0,mutation)
                self.assertFalse(output.exists(),mutation)

if __name__=='__main__': unittest.main()
