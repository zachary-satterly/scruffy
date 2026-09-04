#!/usr/bin/env python3
"""Run the complete dependency-free checks used locally and by CI."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATORS = (
    ('scripts/validate_skill.py',),
    ('scripts/claude_adapter.py', '--check'),
    ('scripts/validate_corpus.py',),
    ('scripts/validate_sources.py',),
    ('scripts/rule_engine.py', '--check'),
    ('mop/scripts/validate_skill.py',),
)


def checks(root: Path = ROOT) -> list[tuple[str, ...]]:
    """Discover new regression scripts so adding a test cannot silently miss CI."""
    tests = sorted(p for directory in (root / 'scripts', root / 'mop/scripts') for p in directory.glob('test_*.py'))
    if not tests:
        raise ValueError('no regression scripts found')
    return [*VALIDATORS, *((p.relative_to(root).as_posix(),) for p in tests)]


def run_checks(commands: list[tuple[str, ...]], *, root: Path = ROOT, timeout: int = 300) -> int:
    failed = []
    for command in commands:
        label = ' '.join(command)
        print(f'\nRUN {label}', flush=True)
        try:
            result = subprocess.run([sys.executable, *command], cwd=root, timeout=timeout, check=False)
            if result.returncode:
                failed.append(label)
        except (OSError, subprocess.TimeoutExpired) as error:
            print(f'FAIL: {label}: {error}', file=sys.stderr, flush=True)
            failed.append(label)
    print(f'\n{len(commands) - len(failed)}/{len(commands)} checks passed', flush=True)
    if failed:
        print('Failed checks:\n' + '\n'.join(failed), file=sys.stderr)
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='list checks without executing them')
    args = parser.parse_args()
    commands = checks()
    if args.list:
        print('\n'.join(' '.join(command) for command in commands))
        return 0
    return run_checks(commands)


if __name__ == '__main__':
    raise SystemExit(main())
