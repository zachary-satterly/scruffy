#!/usr/bin/env python3
"""Offline intake CLI boundaries and truthful capture receipts."""
import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import intake
import validate_corpus

class IntakeTests(unittest.TestCase):
    def test_cli_no_implicit_network(self):
        for args, code in [(['--help'], 0), ([], 2), (['--channel'], 2), (['--unknown'], 2), (['not-a-url'], 2), (['https://example.com/a','--channel','https://example.com/b'],2)]:
            with patch.object(intake, 'sh') as run, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised: intake.main(args)
                self.assertEqual(raised.exception.code, code)
                run.assert_not_called()

    def test_explicit_routes(self):
        with patch.object(intake,'process') as process, patch.object(intake,'list_channel',return_value=['https://example.com/video']) as listing:
            self.assertEqual(intake.main(['--no-frames','https://example.com/video']),0)
            process.assert_called_once_with('https://example.com/video',frames=False)
            listing.assert_not_called()
            self.assertEqual(intake.main(['--channel','https://example.com/channel']),0)
            listing.assert_called_once()

    def test_paths_and_timeout(self):
        for value in ['../escape','a/b','*','',None,'..']:
            with self.assertRaises(ValueError): intake.video_id(value)
        self.assertEqual(intake.video_id('abc_DEF-123'),'abc_DEF-123')
        with patch.object(intake.subprocess,'run') as run:
            intake.sh('tool','arg')
            self.assertEqual(run.call_args.kwargs['timeout'],300)

    def test_metadata_escaping_and_failed_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            base=Path(directory)
            title='Quote " and newline\n---\ninjected: yes'
            metadata={'id':'test-id0001','title':title,'channel':'name: "quoted"','duration':60,'chapters':[{'start_time':0,'title':'Chapter "one"'}]}
            def fake(*args, **kwargs):
                if '-J' in args: return subprocess.CompletedProcess(args,0,json.dumps(metadata),'')
                if '--skip-download' in args:
                    target=Path(args[args.index('-o')+1]+'.en.vtt');target.write_text('WEBVTT\n\n00:00:02.000 --> 00:00:04.000\nHello world\n')
                if '-f' in args: Path(args[args.index('-o')+1]).write_bytes(b'video')
                if args[0]=='ffmpeg': return subprocess.CompletedProcess(args,1,'','failed')
                return subprocess.CompletedProcess(args,0,'','')
            output=io.StringIO()
            with patch.object(intake,'BASE',base),patch.object(intake,'sh',side_effect=fake),contextlib.redirect_stdout(output):
                intake.process('https://example.com/video')
            text=next((base/'transcripts').glob('*.md')).read_text()
            frontmatter=text.split('\n---\n',1)[0]
            title_line=next(line for line in frontmatter.splitlines() if line.startswith('title: '))
            self.assertEqual(json.loads(title_line[len('title: '):]),title)
            self.assertNotIn('injected: yes\n',frontmatter)
            self.assertIn('frame: not captured',text)
            self.assertNotIn('<!-- frame: ../frames/',text)
            self.assertIn('frames: 0/1 captured',output.getvalue())
            self.assertFalse(list((base/'frames').rglob('*.jpg')))
            with patch.object(validate_corpus,'TRANSCRIPTS',base/'transcripts'):
                indexed=validate_corpus.transcript_index()
                self.assertEqual(indexed['test-id0001'][2],60)
                path=indexed['test-id0001'][0]
                path.write_text(text.replace('video_id: "test-id0001"','video_id: test-id0001'))
                self.assertEqual(validate_corpus.transcript_index()['test-id0001'][2],60)

if __name__=='__main__': unittest.main()
