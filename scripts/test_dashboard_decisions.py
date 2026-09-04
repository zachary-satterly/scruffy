#!/usr/bin/env python3
"""Execute the generated dashboard's storage/import handlers in Node's VM."""
import copy
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from render_dashboard import render

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which('node')
HARNESS = r'''
const vm=require('node:vm');
const fs=require('node:fs');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const elements=new Map();
let stored=input.stored===null?null:JSON.stringify(input.stored);
const context=vm.createContext({
  document:{querySelectorAll:()=>[],getElementById:id=>{
    if(!elements.has(id))elements.set(id,{textContent:'',handlers:{},addEventListener(type,fn){this.handlers[type]=fn}});
    return elements.get(id);
  }},
  localStorage:{getItem:()=>stored,setItem:(key,value)=>{stored=value}},
});
vm.runInContext(input.script,context);
(async()=>{
  const initial=JSON.parse(vm.runInContext('JSON.stringify(state)',context));
  if(input.incoming!==null){
    const event={target:{files:[{text:async()=>JSON.stringify(input.incoming)}],value:'chosen'}};
    await elements.get('import-decisions').handlers.change(event);
  }
  process.stdout.write(JSON.stringify({initial,state:JSON.parse(vm.runInContext('JSON.stringify(state)',context)),stored:stored===null?null:JSON.parse(stored),status:elements.get('ui-status')?.textContent||''}));
})().catch(error=>{process.stderr.write(error.stack);process.exitCode=1});
'''


@unittest.skipUnless(NODE, 'Node unavailable: generated JavaScript execution not run')
class DashboardDecisionBinding(unittest.TestCase):
    def setUp(self):
        fixture = ROOT / 'evals' / 'continuity'
        self.registry = json.loads((fixture / 'revision.json').read_text())
        context = json.loads((fixture / 'context.json').read_text())
        self.decisions = json.loads((fixture / 'decisions.json').read_text())
        self.script = re.search(r'<script>(.*?)</script>', render(self.registry, context, self.decisions, fixture / 'context.json'), re.S).group(1)

    def execute(self, *, incoming=None, stored=None):
        result = subprocess.run([NODE, '-e', HARNESS], input=json.dumps({'script': self.script, 'incoming': incoming, 'stored': stored}), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def valid_update(self):
        incoming = copy.deepcopy(self.decisions)
        incoming['decisions'][0]['decision'] = 'approve'
        incoming['decisions'][0]['note'] = 'Current review approval'
        return incoming

    def test_current_import_and_legacy_storage_key_remain_usable(self):
        incoming = self.valid_update()
        result = self.execute(incoming=incoming)
        self.assertEqual(result['state'], incoming)
        self.assertEqual(result['stored'], incoming)
        self.assertIn('imported', result['status'])
        self.assertEqual(self.execute(stored=incoming)['state'], incoming)

    def test_bindings_reject_stale_import_and_saved_approvals_without_rewriting(self):
        for field in ('schema_version', 'audit_id', 'revision_id', 'baseline_revision_id'):
            incoming = self.valid_update(); incoming[field] = 'foreign'
            with self.subTest(field=field):
                result = self.execute(incoming=incoming)
                self.assertEqual(result['state'], self.decisions)
                self.assertIsNone(result['stored'])
                self.assertIn('Import rejected', result['status'])
                result = self.execute(stored=incoming)
                self.assertEqual(result['state'], self.decisions)
                self.assertEqual(result['stored'], incoming)
                self.assertIn('Saved decisions rejected', result['status'])

    def test_duplicate_missing_unknown_malformed_and_terminal_decisions_are_rejected(self):
        terminal = next(item['id'] for item in self.registry['items'] if item['kind'] in ('finding','enhancement') and item['status'] not in ('open','needs-verification'))
        def terminal_mutation(doc):
            next(row for row in doc['decisions'] if row['item_id'] == terminal)['decision'] = 'approve'
        for mutate in (
            lambda d: d['decisions'].pop(),
            lambda d: d['decisions'].__setitem__(1, copy.deepcopy(d['decisions'][0])),
            lambda d: d['decisions'][0].update(item_id='AS-UNKNOWN'),
            lambda d: d['decisions'][0].update(decision='execute'),
            lambda d: d['decisions'][0].update(note={}),
            lambda d: d['decisions'][0].update(history={}),
            lambda d: d['decisions'][0].update(history=[{'decision':'approve','note':{},'updated_at':None}]),
            lambda d: d['decisions'][0].update(destination_id='AS-OTHER'),
            terminal_mutation,
        ):
            incoming=self.valid_update(); mutate(incoming)
            result=self.execute(incoming=incoming, stored=self.valid_update())
            self.assertEqual(result['state'], self.valid_update())
            self.assertEqual(result['stored'], self.valid_update())
            self.assertIn('Import rejected', result['status'])


if __name__ == '__main__':
    unittest.main()
