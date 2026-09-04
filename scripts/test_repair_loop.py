#!/usr/bin/env python3
"""An approved repair must produce proof before a new revision closes it."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scaffold_audit import build

ROOT = Path(__file__).resolve().parents[1]

class RepairLoop(unittest.TestCase):
    def test_authorized_repair_to_reaudit_and_outcomes(self):
        with tempfile.TemporaryDirectory() as raw:
            bundle=Path(raw)
            registry,context,decisions=build('loop','Local loop fixture','Loop fixture','LP','redesign','authorized',[])
            item=registry['items'][0];item['category']='backend_shape';item['status']='open'
            item['acceptance_checks']=['The local output says ready.']
            item['fix_packet']={'target':[{'kind':'file','value':'output.txt'}],
                'change':'Write the expected readiness state.','effort':'S','rollback':'Restore the previous output.',
                'acceptance':[{'kind':'command','run':f'"{sys.executable}" -c "from pathlib import Path; assert Path(\'output.txt\').read_text() == \'ready\'"','summary':'Read the actual repaired file.','check_ref':0}]}
            decisions['decisions'][0]['decision']='approve'
            for name,data in [('findings.json',registry),('context.json',context),('decisions.json',decisions)]:
                (bundle/name).write_text(json.dumps(data))
            def run(script,*args,success=True):
                proc=subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=bundle,capture_output=True,text=True)
                self.assertEqual(proc.returncode==0,success,proc.stdout+proc.stderr)
                return proc.stdout
            (bundle/'output.txt').write_text('broken')
            run('mop/scripts/mop_run.py',bundle,'--authorized')
            original=(bundle/'findings.json').read_bytes()
            verify=['scripts/verify_fixes.py',bundle/'findings.json','--decisions',bundle/'decisions.json','--cwd',bundle,'--execute','--output',bundle/'verification.json']
            run(*verify,success=False)
            (bundle/'output.txt').write_text('ready')
            run(*verify)
            (bundle/'work.json').write_text(json.dumps({'LP-1':{'surfaces':['output.txt'],'self_check':[{'check':item['acceptance_checks'][0],'result':'meets'}]}}))
            handoff=json.loads(run('mop/scripts/mop_handoff.py',bundle,'--authorized','--work',bundle/'work.json','--json'))
            self.assertEqual(handoff['items'][0]['verification']['result'],'verified')
            self.assertEqual(handoff['items'][0]['status'],'implemented-pending-reaudit')
            self.assertEqual((bundle/'findings.json').read_bytes(),original)
            # The re-auditor independently observes the acceptance state.
            self.assertEqual((bundle/'output.txt').read_text(),'ready')
            current=copy.deepcopy(registry);current['revision_id']='loop-r2';current['baseline_revision_id']=registry['revision_id']
            current['items'][0].update(status='fixed',revision_disposition='fixed',last_observed_revision='loop-r2',disposition_reason='Re-read local output and matched the approved acceptance state.')
            current['presentation']['prioritized_finding_ids']=[];current['presentation']['cleared_ids']=['LP-1']
            (bundle/'revision.json').write_text(json.dumps(current))
            next_context=copy.deepcopy(context)
            next_context.update(revision_id='loop-r2',baseline_revision_id=registry['revision_id'])
            for route in next_context['routing']:
                route.update(last_observed_revision='loop-r2',revision_disposition='carried',disposition_reason='Same scope rechecked.')
            (bundle/'revision-context.json').write_text(json.dumps(next_context))
            validation=['scripts/validate_audit.py',bundle/'revision.json','--context',bundle/'revision-context.json','--baseline',bundle/'findings.json','--baseline-context',bundle/'context.json']
            run(*validation,success=False)
            run(*validation,'--verification',bundle/'verification.json')
            run('scripts/outcomes.py',f'{bundle}/findings.json:{bundle}/decisions.json:{bundle}/verification.json',bundle/'revision.json','--output',bundle/'outcomes.json')
            total=json.loads((bundle/'outcomes.json').read_text())['total']
            self.assertEqual((total['approved'],total['verified'],total['fixed']),(1,1,1))

if __name__=='__main__': unittest.main()
