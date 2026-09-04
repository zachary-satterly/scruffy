#!/usr/bin/env python3
"""Exercise suite discovery and nonzero/timeout propagation with real children."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from check import checks, run_checks


class CheckRunner(unittest.TestCase):
    def test_both_test_directories_and_new_tests_are_discovered(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            for name in ('scripts/test_new.py', 'mop/scripts/test_repair.py', 'scripts/helper.py'):
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.touch()
            commands = checks(root)
            self.assertIn(('scripts/test_new.py',), commands)
            self.assertIn(('mop/scripts/test_repair.py',), commands)
            self.assertNotIn(('scripts/helper.py',), commands)
            self.assertEqual(len(commands), len(set(commands)))

    def test_failure_does_not_hide_later_results(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'fail.py').write_text('raise SystemExit(7)')
            (root / 'pass.py').write_text('from pathlib import Path; Path("ran").touch()')
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(run_checks([('fail.py',), ('pass.py',)], root=root), 1)
                self.assertTrue((root / 'ran').exists())
                self.assertEqual(run_checks([('pass.py',)], root=root), 0)
                (root / 'slow.py').write_text('import time; time.sleep(10)')
                self.assertEqual(run_checks([('slow.py',)], root=root, timeout=1), 1)


if __name__ == '__main__':
    unittest.main()
