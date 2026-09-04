#!/usr/bin/env python3
"""Exercise canonical generator safety and immutable evaluation preparation."""
import argparse
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
import audit_contract
import taxonomy_contract
import run_review_routing_eval as runner
import evaluate_review_routing as evaluator

class GeneratorGuards(unittest.TestCase):
    def test_literal_projection_text(self):
        for module in (audit_contract,taxonomy_contract):
            old=module.README_START+'\nold\n'+module.README_END
            for value in (r'C:\Users\example',r'Literal \1 and \n',r'A | B'):
                new=module.README_START+'\n'+value+'\n'+module.README_END
                self.assertEqual(module.replace_readme_block(old,new),new)

    def test_mode_boolean_types(self):
        data=json.loads(audit_contract.MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'contract.json'
            for field in ('repository_writes_allowed','live_demonstration_allowed'):
                for value in ('false',0,None):
                    changed=json.loads(json.dumps(data));changed['run']['modes'][0][field]=value;path.write_text(json.dumps(changed))
                    with self.assertRaisesRegex(ValueError,'must be a boolean'):audit_contract.load_contract(path)
            path.write_text(json.dumps(data));audit_contract.load_contract(path)

    def test_layer_links(self):
        data=json.loads(taxonomy_contract.MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'taxonomy.json';path.write_text(json.dumps(data));taxonomy_contract.load_taxonomy(path)
            data['categories'][0]['inspection_layer']=data['inspection_layers'][-1]['key'];path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'contradicts'):taxonomy_contract.load_taxonomy(path)

    def test_run_paths_and_frozen_evidence(self):
        with tempfile.TemporaryDirectory() as raw:
            base=Path(raw)
            args=argparse.Namespace(repetitions=1,run_id='review-2026',agent='test',output=base/'run',scoring_key=runner.DEFAULT_DEVELOPMENT_KEY,evidence_class='public_development',provider='test',model='test',runtime='test',runtime_version='1',cases=runner.DEFAULT_CASES,archetypes=runner.DEFAULT_ARCHETYPES)
            for bad in ('../escape','../../escape','/absolute','a/b','a\\b',''):
                args.run_id=bad
                with self.assertRaisesRegex(ValueError,'run-id'):runner.prepare(args)
                self.assertEqual(list(base.iterdir()),[])
            args.run_id='review-2026'
            with contextlib.redirect_stdout(io.StringIO()):runner.prepare(args)
            manifest_path=args.output/'run-manifest.json';before=manifest_path.read_bytes();manifest=json.loads(before)
            self.assertEqual(evaluator.validate_manifest(manifest,args.scoring_key),[])
            receipt=Path(manifest['trials'][0]['expected_session_receipt']);receipt.write_text('preserve receipt')
            with self.assertRaisesRegex(ValueError,'already exists'):runner.prepare(args)
            self.assertEqual(manifest_path.read_bytes(),before);self.assertEqual(receipt.read_text(),'preserve receipt')
            for path in [manifest['trials'][0][key] for key in ('prompt','expected_result','expected_session_receipt')]:
                self.assertTrue(Path(path).is_relative_to(args.output.resolve()))

if __name__=='__main__':unittest.main()
