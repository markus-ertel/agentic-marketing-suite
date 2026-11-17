"""Test helper: a fictional signing key outside the test root, exposed like the approving harness would."""
import os
from pathlib import Path
import tempfile
from unittest import mock


def use_test_key(case):
    folder = tempfile.TemporaryDirectory()
    case.addCleanup(folder.cleanup)
    path = Path(folder.name) / 'approval.key'
    path.write_text('fictional-test-signing-key-' + 'x' * 40 + '\n')
    patcher = mock.patch.dict(os.environ, {'SUITE_APPROVAL_KEY_FILE': str(path)})
    patcher.start()
    case.addCleanup(patcher.stop)
    return path.read_bytes().strip()
