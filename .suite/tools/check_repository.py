#!/usr/bin/env python3
"""Offline repository checks using only the Python standard library."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {'.git', '.venv', 'venv', '__pycache__', 'node_modules'}
MODULES = {
    'marketing': '.marketing', 'pr': '.pr', 'social-media': '.social-media',
    'website': '.nocms', 'advertising': '.advertising', 'creative': '.creative',
    'noCRM': '.nocrm', 'analytics': '.analytics', 'e-commerce': '.e-commerce',
}


def check_files():
    errors = []
    required = [
        'README.md', 'LICENSE.md', 'AGENT.md', '.gitignore', 'CONTRIBUTING.md',
        'SECURITY.md', 'MIGRATION.md', '.github/workflows/checks.yml',
        '.suite/ARCHITECTURE.md', '.suite/QUALITY.md', '.suite/GOVERNANCE.md',
    ]
    for module, internal in MODULES.items():
        required.extend([f'{module}/AGENT.md', f'{module}/{internal}/METHODEN.md'])
    for name in required:
        path = ROOT / name
        if not path.is_file() or not path.stat().st_size:
            errors.append(f'Missing or empty required file: {name}')
    counts = {'Markdown': 0, 'JSON': 0}
    for directory, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = Path(directory) / name
            relative = path.relative_to(ROOT)
            if path.suffix == '.json':
                counts['JSON'] += 1
                try:
                    json.loads(path.read_text(encoding='utf-8'))
                except (ValueError, OSError) as exc:
                    errors.append(f'{relative}: {exc}')
            elif path.suffix == '.md':
                counts['Markdown'] += 1
                for href in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                    if href.startswith('#') or urlsplit(href).scheme:
                        continue
                    target = unquote(href.split('#', 1)[0])
                    if target and not (path.parent / target).exists():
                        errors.append(f'{relative}: missing local link target {href}')
    print(f'Documentation: {counts["Markdown"]} Markdown, {counts["JSON"]} JSON files', flush=True)
    for error in errors:
        print(f'FAIL: {error}', file=sys.stderr)
    return not errors


def main():
    if not check_files():
        return 1
    commands = [
        ['-m', 'unittest', 'discover', '-s', directory, '-v']
        for directory in (
            '.suite/tests', 'analytics/.analytics/tests',
            'creative/.creative/tests', 'noCRM/.nocrm/tests',
            'e-commerce/.e-commerce/tests',
        )
    ]
    commands.extend([
        ['advertising/.advertising/tools/test_workspace.py'],
        ['.suite/tools/validate_records.py', 'work-order', '.suite/beispiele/topaca-work-order.json'],
        ['.suite/tools/validate_records.py', 'bundle', '.suite/beispiele/demo-freigabe-bundle.json'],
        ['social-media/.social-media/tools/validate_job.py', 'social-media/.social-media/integrationen/BEISPIEL_JOB.json'],
        ['advertising/.advertising/tools/validate_manifest.py', 'advertising/.advertising/beispiele/DRAFT_MANIFEST_DEMO.json'],
        ['e-commerce/.e-commerce/tools/generate_gmc_feed.py', '-i', 'e-commerce/.e-commerce/beispiele/katalog-demo.csv', '--check-only', '--strict'],
        ['e-commerce/.e-commerce/tools/validate_compliance.py', '--offers', 'e-commerce/.e-commerce/beispiele/funnel-demo.json',
         '--catalog', 'e-commerce/.e-commerce/beispiele/katalog-demo.json'],
    ])
    failed = False
    for command in commands:
        print('\nRunning: ' + ' '.join(command), flush=True)
        result = subprocess.run([sys.executable, *command], cwd=ROOT, check=False)
        failed |= result.returncode != 0
    if failed:
        return 1
    print('\nPASS: repository structure, local link targets, JSON syntax, tests and demo preflights.')
    print('No external actions or compliance certification.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
