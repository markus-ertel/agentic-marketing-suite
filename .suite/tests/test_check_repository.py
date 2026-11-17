"""The link checker must not probe paths outside the repository."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('check_repository', ROOT / '.suite/tools/check_repository.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class LinkContainmentTests(unittest.TestCase):
    def test_links_outside_the_repository_are_errors_not_probes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'repo'
            (root / 'docs').mkdir(parents=True)
            (root / 'docs/ok.md').write_text('x')
            outside = Path(temp) / 'outside.txt'
            outside.write_text('exists outside the repository')
            (root / 'docs/a.md').write_text('[ok](ok.md) [esc](../../outside.txt) [missing](nope.md)')
            probed = []
            original = Path.exists
            def spy(path):
                probed.append(Path(path).resolve())
                return original(path)
            stderr = io.StringIO()
            with mock.patch.object(checker, 'ROOT', root.resolve()), mock.patch.object(Path, 'exists', spy), \
                    redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                ok = checker.check_files()
            self.assertFalse(ok)
            self.assertNotIn(outside.resolve(), probed)
            self.assertIn('docs/a.md: link target escapes repository ../../outside.txt', stderr.getvalue())
            self.assertIn('docs/a.md: missing local link target nope.md', stderr.getvalue())
            self.assertNotIn('ok.md', stderr.getvalue())
